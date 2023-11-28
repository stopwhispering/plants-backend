from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from plants import settings
from plants.exceptions import PlantAlreadyExistsError
from plants.modules.plant.models import Plant, Tag
from plants.modules.plant.util import (
    has_roman_plant_index,
    int_to_roman,
    parse_roman_plant_index,
    roman_to_int,
)
from plants.shared.orm_util import clone_orm_instance

if TYPE_CHECKING:
    from plants.modules.event.event_dal import EventDAL
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.plant.schemas import PlantCreate, PlantTag, PlantUpdate, TaxonTag
    from plants.modules.pollination.models import SeedPlanting
    from plants.modules.taxon.models import Taxon
    from plants.modules.taxon.taxon_dal import TaxonDAL

logger = logging.getLogger(__name__)


async def create_new_plant(
    new_plant: PlantCreate, plant_dal: PlantDAL, taxon_dal: TaxonDAL
) -> Plant:
    if await plant_dal.exists(new_plant.plant_name):
        raise PlantAlreadyExistsError(new_plant.plant_name)
    # await plant_dal.create_empty_plant(plant_name=new_plant.plant_name)

    new_plant_data = new_plant.model_dump(exclude={"tags", "parent_plant", "parent_plant_pollen"})
    new_plant_data["parent_plant_id"] = (
        new_plant.parent_plant.id if new_plant.parent_plant else None
    )
    new_plant_data["parent_plant_pollen_id"] = (
        new_plant.parent_plant_pollen.id if new_plant.parent_plant_pollen else None
    )
    new_plant_data["taxon"] = (
        await taxon_dal.by_id(new_plant.taxon_id) if new_plant.taxon_id else None
    )
    plant = await plant_dal.create_plant(new_plant_data)
    await _treat_tags(plant, new_plant.tags, plant_dal=plant_dal)
    return plant


async def update_plants_from_list_of_dicts(
    plants: list[PlantUpdate], plant_dal: PlantDAL, taxon_dal: TaxonDAL
) -> list[Plant]:
    plants_saved = []
    logger.info(f"Updating {len(plants)} plants")
    for plant in plants:
        record_update = await plant_dal.by_id(plant.id)

        # update plant
        updates = plant.model_dump(
            exclude={"id", "tags", "taxon_tags", "parent_plant", "parent_plant_pollen"}
        )

        updates["parent_plant_id"] = plant.parent_plant.id if plant.parent_plant else None
        updates["parent_plant_pollen_id"] = (
            plant.parent_plant_pollen.id if plant.parent_plant_pollen else None
        )

        taxon = await taxon_dal.by_id(plant.taxon_id) if plant.taxon_id else None
        updates["taxon"] = taxon

        await plant_dal.update(record_update, updates)

        # create new, update existing and remove deleted tags
        await _treat_tags(record_update, plant.tags, plant_dal=plant_dal)
        plants_saved.append(record_update)

        if taxon:
            await _treat_taxon_tags(taxon=taxon, taxon_tags=plant.taxon_tags, taxon_dal=taxon_dal)

    return plants_saved


async def deep_clone_plant(
    plant_original: Plant,
    plant_name_clone: str,
    plant_dal: PlantDAL,
    event_dal: EventDAL,
) -> None:
    """clone supplied plant includes duplication of events, photo_file-to-event assignments, tags
    excludes descendant plants assignments to same instances of parent plants, parent plants pollen
    (nothing to do here)"""
    plant_clone: Plant = clone_orm_instance(
        plant_original,
        {
            "plant_name": plant_name_clone,
            # "filename_previewimage": None,
        },
    )

    cloned_tags = []
    for tag in plant_original.tags:
        tag_clone = clone_orm_instance(tag, {})
        tag_clone.plant = plant_clone
        cloned_tags.append(tag_clone)
    if cloned_tags:
        plant_clone.tags.extend(cloned_tags)
        # await plant_dal.create_tags(cloned_tags)

    cloned_events = []
    for event in plant_original.events:
        event_clone = clone_orm_instance(event)
        event_clone.plant = plant_clone
        cloned_events.append(event_clone)

        # photo_file-to-event associations via photo_file instances (no need to update
        # these explicitly)
        await event_dal.add_images_to_event(event_clone, event.images)

    if cloned_events:
        await event_dal.create_events(cloned_events)

    await plant_dal.save_plant(plant_clone)


async def _treat_taxon_tags(taxon: Taxon, taxon_tags: list[TaxonTag], taxon_dal: TaxonDAL) -> None:
    """Add/remove taxon tags."""
    old_tag_texts = {t.text for t in taxon.tags}

    # new tags with no id, yet
    new_tags = [t for t in taxon_tags if t.text not in old_tag_texts]
    _ = await taxon_dal.add_tags_to_taxon(taxon, new_tags) if new_tags else []

    # update existing tags is not implemented in frontend)
    # todo: make it possible to change status

    # deleted tags not supplied anymore
    new_tag_texts = {t.text for t in taxon_tags}
    deleted_tags = [t for t in taxon.tags if t.text not in new_tag_texts]
    if deleted_tags:
        await taxon_dal.remove_tags_from_taxon(taxon, deleted_tags)


async def _treat_tags(plant: Plant, tags: list[PlantTag], plant_dal: PlantDAL) -> None:
    """Update modified tags; returns list of new tags (not yet added or committed); removes deleted
    tags."""
    # create new tags
    new_tags = []
    for tag in [t for t in tags if t.id is None]:
        new_tag: Tag = Tag(
            text=tag.text,
            state=tag.state,
            plant=plant,
            # taxon=
        )
        new_tags.append(new_tag)
    if new_tags:
        plant.tags.extend(new_tags)
    # await plant_dal.create_tags(new_tags)

    # update existing tags (not currently implemented in frontend)
    for tag in tags:
        if tag.id is None:
            continue
        tag_object = await plant_dal.get_tag_by_tag_id(tag.id)
        await plant_dal.update_tag(tag_object, tag.model_dump())

    # delete tags not supplied anymore
    updated_ids = {t.id for t in tags if t.id is not None}
    created_ids = {t.id for t in new_tags}
    deleted_tags = [t for t in plant.tags if t.id not in updated_ids.union(created_ids)]
    for deleted_tag in deleted_tags:
        await plant_dal.remove_tag_from_plant(plant, deleted_tag)


async def fetch_plants(plant_dal: PlantDAL) -> list[Plant]:
    return await plant_dal.get_all_plants_with_relationships(
        include_deleted=not settings.plants.filter_hidden
    )


def generate_subsequent_plant_name(original_plant_name: str) -> str:
    """Derive subsequent name for supplied plant name, e.g. "Aloe depressa VI" for "Aloe depressa
    V"."""
    if has_roman_plant_index(original_plant_name):
        plant_name, roman_plant_index = parse_roman_plant_index(original_plant_name)
        plant_index = roman_to_int(roman_plant_index)
    else:
        plant_name, plant_index = original_plant_name, 1

    return f"{plant_name} {int_to_roman(plant_index + 1)}"


async def generate_plant_name_proposal_for_seed_planting(
    seed_planting: SeedPlanting, plant_dal: PlantDAL
) -> str:
    """Generate a plant name proposal for a seed planting."""
    seed_capsule_plant: Plant = seed_planting.pollination.seed_capsule_plant
    pollen_donor_plant: Plant = seed_planting.pollination.pollen_donor_plant
    plant_name = f"{seed_capsule_plant.plant_name} × {pollen_donor_plant.plant_name}"
    while await plant_dal.exists(plant_name):  # pylint: disable=W0149
        plant_name = generate_subsequent_plant_name(plant_name)
    return plant_name

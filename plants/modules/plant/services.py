import logging
from typing import List, Optional

from plants import settings
from plants.exceptions import PlantAlreadyExists
from plants.modules.event.event_dal import EventDAL
from plants.modules.plant.models import Plant, Tag
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.plant.schemas import FBPlantTag, PlantCreateUpdate
from plants.modules.plant.util import (has_roman_plant_index, int_to_roman,
                                       parse_roman_plant_index, roman_to_int)
# from plants.modules.property.property_dal import PropertyDAL
from plants.modules.taxon.taxon_dal import TaxonDAL

logger = logging.getLogger(__name__)


async def _add_new_plant(plant_name: str, plant_dal: PlantDAL) -> Plant:
    if await plant_dal.exists(plant_name):
        raise PlantAlreadyExists(plant_name)
    new_plant = await plant_dal.create_empty_plant(plant_name=plant_name)
    return new_plant


# todo this is still required (otherwise save error) - why? replcae
def _get_filename_previewimage(plant: Optional[PlantCreateUpdate] = None) -> str | None:
    """We actually set the path to preview photo_file (the original photo_file,
    not the thumbnail) excluding the photos-subdir part of the uri."""
    if not plant.filename_previewimage:
        return None

    # generate_previewimage_if_not_exists(original_image_rel_path=plant.filename_previewimage)

    # rmeove photos-subdir from path if required (todo: still required somewhere?)
    if plant.filename_previewimage.is_relative_to(settings.paths.subdirectory_photos):
        return plant.filename_previewimage.relative_to(
            settings.paths.subdirectory_photos
        ).as_posix()
    else:
        return plant.filename_previewimage.as_posix()


async def update_plants_from_list_of_dicts(
    plants: List[PlantCreateUpdate], plant_dal: PlantDAL, taxon_dal: TaxonDAL
) -> List[Plant]:
    plants_saved = []
    logger.info(f"Updating/Creating {len(plants)} plants")
    for plant in plants:
        if plant.id is None:
            # create the plant and flush to get plant id
            record_update = await _add_new_plant(plant.plant_name, plant_dal)
        else:
            record_update = await plant_dal.by_id(plant.id)

        # update plant
        updates = plant.dict(
            exclude={"id", "tags", "parent_plant", "parent_plant_pollen"}
        )

        updates["parent_plant_id"] = (
            plant.parent_plant.id if plant.parent_plant else None
        )
        updates["parent_plant_pollen_id"] = (
            plant.parent_plant_pollen.id if plant.parent_plant_pollen else None
        )
        updates["filename_previewimage"] = _get_filename_previewimage(plant)
        updates["taxon"] = (
            await taxon_dal.by_id(plant.taxon_id) if plant.taxon_id else None
        )

        await plant_dal.update(record_update, updates)

        # create new, update existing and remove deleted tags
        await _treat_tags(record_update, plant.tags, plant_dal=plant_dal)
        plants_saved.append(record_update)

    return plants_saved


def _clone_instance(model_instance, clone_attrs: Optional[dict] = None):
    """Generate a transient clone of sqlalchemy instance; supply primary key as
    dict."""
    # get data of non-primary-key columns; exclude relationships
    table = model_instance.__table__
    non_pk_columns = [k for k in table.columns.keys() if k not in table.primary_key]
    data = {c: getattr(model_instance, c) for c in non_pk_columns}
    if clone_attrs:
        data.update(clone_attrs)
    return model_instance.__class__(**data)


async def deep_clone_plant(
    plant_original: Plant,
    plant_name_clone: str,
    plant_dal: PlantDAL,
    event_dal: EventDAL,
    # property_dal: PropertyDAL,
):
    """clone supplied plant includes duplication of events, photo_file-to-event
    assignments, tags excludes descendant plants assignments to same instances
    of parent plants, parent plants pollen (nothing to do here)"""
    plant_clone: Plant = _clone_instance(
        plant_original,
        {
            "plant_name": plant_name_clone,  # noqa
            "filename_previewimage": None,
        },
    )

    cloned_tags = []
    for tag in plant_original.tags:
        # tag_clone = _clone_instance(tag, {'last_update': datetime.now()})  # noqa
        tag_clone = _clone_instance(tag, {})  # noqa
        tag_clone.plant = plant_clone
        cloned_tags.append(tag_clone)
    if cloned_tags:
        await plant_dal.create_tags(cloned_tags)

    cloned_events = []
    for event in plant_original.events:
        event_clone = _clone_instance(event)  # noqa
        event_clone.plant = plant_clone
        cloned_events.append(event_clone)

        # photo_file-to-event associations via photo_file instances (no need to update these explicitly)
        await event_dal.add_images_to_event(event_clone, event.images)

    if cloned_events:
        await event_dal.create_events(cloned_events)

    await plant_dal.create_plant(plant_clone)


async def _treat_tags(plant: Plant, tags: List[FBPlantTag], plant_dal: PlantDAL):
    """Update modified tags; returns list of new tags (not yet added or
    committed); removes deleted tags."""
    new_tags = []

    # create new tags
    for tag in [t for t in tags if t.id is None]:
        new_tag: Tag = Tag(
            text=tag.text,
            state=tag.state,
            plant=plant,
        )
        new_tags.append(new_tag)
    await plant_dal.create_tags(new_tags)

    # update existing tags (not currently implemented in frontend)
    for updated_tag in [t for t in tags if t.id is not None]:
        tag_object = await plant_dal.get_tag_by_tag_id(updated_tag.id)
        await plant_dal.update_tag(tag_object, updated_tag.dict())

    # delete tags not supplied anymore
    updated_plant_ids = set((t.id for t in tags if t.id is not None))
    for deleted_tag in [t for t in plant.tags if t.id not in updated_plant_ids]:
        await plant_dal.remove_tag_from_plant(plant, deleted_tag)


async def fetch_plants(plant_dal: PlantDAL) -> list[Plant]:
    plants = await plant_dal.get_all_plants_with_relationships_loaded(
        include_deleted=not settings.plants.filter_hidden
    )
    return plants


def generate_subsequent_plant_name(original_plant_name: str) -> str:
    """Derive subsequent name for supplied plant name, e.g. "Aloe depressa VI"
    for "Aloe depressa V"."""
    if has_roman_plant_index(original_plant_name):
        plant_name, roman_plant_index = parse_roman_plant_index(original_plant_name)
        plant_index = roman_to_int(roman_plant_index)
    else:
        plant_name, plant_index = original_plant_name, 1

    return f"{plant_name} {int_to_roman(plant_index + 1)}"

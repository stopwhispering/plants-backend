from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from plants.exceptions import (CriterionNotImplemented, PlantNotFound,
                               TagNotAssignedToPlant, TagNotFound,
                               UpdateNotImplemented)
from plants.modules.event.models import Event
from plants.modules.image.models import Image, ImageToPlantAssociation
from plants.modules.plant.models import Plant, Tag
from plants.modules.taxon.models import Taxon
from plants.shared.base_dal import BaseDAL


class PlantDAL(BaseDAL):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    @staticmethod
    def _add_eager_load_options(query: Select) -> Select:
        """Apply eager loading the query supplied; use only for single- or
        limited-number select queries to avoid performance issues."""
        query = query.options(
            selectinload(Plant.parent_plant),
            selectinload(Plant.parent_plant_pollen),
            selectinload(Plant.tags),
            selectinload(Plant.same_taxon_plants),
            selectinload(Plant.sibling_plants),
            selectinload(Plant.descendant_plants),
            selectinload(Plant.descendant_plants_pollen),
            selectinload(Plant.taxon),
            selectinload(Plant.events).selectinload(Event.soil),
            selectinload(Plant.events).selectinload(Event.observation),
            selectinload(Plant.events).selectinload(Event.pot),
            selectinload(Plant.events).selectinload(Event.images),
            selectinload(Plant.images).selectinload(Image.keywords),
            selectinload(Plant.florescences),
        )
        return query

    async def by_id(self, plant_id: int, eager_load=True) -> Plant:
        query = (
            select(Plant)
            .where(Plant.id == plant_id)  # noqa
            .where(Plant.deleted.is_(False))
            .limit(1)
        )

        if eager_load:
            query = self._add_eager_load_options(query)

        plant: Plant = (await self.session.scalars(query)).first()  # noqa
        if not plant:
            raise PlantNotFound(plant_id)
        return plant

    async def by_name(
        self, plant_name: str, eager_load=True, only_active=True
    ) -> Plant:
        query = (
            select(Plant)
            .where(Plant.plant_name == plant_name)  # noqa
            .where(Plant.deleted.is_(False))
            .limit(1)
        )

        if only_active:
            query = query.where(Plant.active)

        if eager_load:
            query = self._add_eager_load_options(query)

        plant: Plant = (await self.session.scalars(query)).first()
        return plant

    async def get_plant_ids_by_taxon_id(
        self, taxon_id: int, eager_load=True, only_active=True
    ) -> list[int]:
        query = (
            select(Plant.id)
            .where(Plant.taxon_id == taxon_id)  # noqa
            .where(Plant.deleted.is_(False))
        )

        if only_active:
            query = query.where(Plant.active)

        if eager_load:
            query = self._add_eager_load_options(query)

        plants: list[int] = (await self.session.scalars(query)).all()  # noqa
        # todo does it reutrn tuple or list??
        return plants

    async def get_plant_by_criteria(self, criteria: dict) -> list[Plant]:
        query = select(Plant).where(Plant.deleted.is_(False))  # .filter_by(**criteria)
        for key, value in criteria.items():
            if "field_number" in key:
                value: str
                query = query.filter(Plant.field_number == value)
            else:
                raise CriterionNotImplemented(key)
        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

    async def get_name_by_id(self, plant_id: int) -> str:
        query = (
            select(Plant.plant_name)
            .where(Plant.id == plant_id)  # noqa
            .where(Plant.deleted.is_(False))
            .limit(1)
        )
        plant_name: str = (await self.session.scalars(query)).first()
        if not plant_name:
            raise PlantNotFound(plant_id)
        return plant_name

    async def get_id_by_name(self, plant_name: str) -> int:
        query = (
            select(Plant.id)
            .where(Plant.plant_name == plant_name)  # noqa
            .where(Plant.deleted.is_(False))
            .limit(1)
        )
        plant_id: int = (await self.session.scalars(query)).first()
        if not plant_id:
            raise PlantNotFound(plant_name)
        return plant_id

    async def get_count_plants_without_taxon(self) -> int:
        query = (
            select(func.count())
            .select_from(Plant)
            .where(Plant.taxon_id.is_(None))
            .where(Plant.deleted.is_(False))
            .where(Plant.active)
        )
        count: int = (await self.session.scalars(query)).first()  # noqa
        return count

    async def get_plants_ids_without_taxon(self) -> list[int]:
        query = (
            select(Plant.id)
            .where(Plant.taxon_id.is_(None))
            .where(Plant.deleted.is_(False))
            .where(Plant.active)
        )
        plant_ids: list[int] = (await self.session.scalars(query)).all()  # noqa
        return plant_ids

    async def create_plant(self, plant: Plant):
        self.session.add(plant)
        await self.session.flush()

    async def create_empty_plant(self, plant_name: str) -> Plant:
        new_plant = Plant(plant_name=plant_name, deleted=False, active=True)
        self.session.add(new_plant)
        await self.session.flush()
        return await self.by_id(new_plant.id)  # adds eager load options

    async def create_tags(self, tags: list[Tag]):
        self.session.add_all(tags)
        await self.session.flush()

    async def get_all_plants_with_taxon(self) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))
            .options(selectinload(Plant.taxon))
        )
        return (await self.session.scalars(query)).all()  # noqa

    async def set_count_stored_pollen_containers(self, plant: Plant, count: int):
        plant.count_stored_pollen_containers = count
        await self.session.flush()

    async def get_plants_without_pollen_containers(self) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))
            .where(Plant.active)
            .where(
                (Plant.count_stored_pollen_containers == 0)
                | Plant.count_stored_pollen_containers.is_(None)
            )
            .where((Plant.deleted.is_(False)))
            .options(selectinload(Plant.taxon))
        )
        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

    async def get_plants_with_pollen_containers(self) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))
            .where(Plant.count_stored_pollen_containers >= 1)
            .options(selectinload(Plant.taxon))
        )
        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

    async def get_children(
        self, seed_capsule_plant: Plant, pollen_donor_plant: Plant
    ) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))
            .where(
                Plant.parent_plant_id == seed_capsule_plant.id,
                Plant.parent_plant_pollen_id == pollen_donor_plant.id,
            )
        )

        children: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return children

    async def get_children_by_ids(
        self, seed_capsule_plant_id: int, pollen_donor_plant_id: int
    ) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))
            .where(
                Plant.parent_plant_id == seed_capsule_plant_id,
                Plant.parent_plant_pollen_id == pollen_donor_plant_id,
            )
        )

        children: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return children

    async def exists(self, plant_name: str) -> bool:
        query = select(Plant).where(Plant.plant_name == plant_name).limit(1)  # noqa
        plant: Plant = (await self.session.scalars(query)).first()
        return plant is not None

    async def delete(self, plant: Plant):
        plant.deleted = True
        await self.session.flush()

    async def get_distinct_nurseries(self) -> list[str]:
        query = (
            select(Plant.nursery_source)
            .where(Plant.nursery_source.isnot(None))
            .distinct(Plant.nursery_source)
        )
        nurseries: list[str] = (await self.session.scalars(query)).all()  # noqa
        return nurseries

    async def update(self, plant: Plant, updates: dict):
        for key, value in updates.items():
            if key == "plant_name":
                value: str
                plant.plant_name = value
            elif key == "active":
                value: bool
                plant.active = updates["active"]
            elif key == "cancellation_reason":
                value: str | None
                plant.cancellation_reason = value
            elif key == "cancellation_date":
                value: datetime | None
                plant.cancellation_date = value
            elif key == "field_number":
                value: str | None
                plant.field_number = value
            elif key == "geographic_origin":
                value: str | None
                plant.geographic_origin = value
            elif key == "nursery_source":
                value: str | None
                plant.nursery_source = value
            elif key == "propagation_type":
                value: str | None
                plant.propagation_type = value
            elif key == "generation_notes":
                value: str | None
                plant.generation_notes = value
            elif key == "plant_notes":
                value: str | None
                plant.plant_notes = value
            elif key == "parent_plant_id":
                value: int | None
                plant.parent_plant_id = value
            # elif key == 'parent_plant':
            #     value: Plant | None
            #     plant.parent_plant = value
            elif key == "parent_plant_pollen_id":
                value: int | None
                plant.parent_plant_pollen_id = value
            elif key == "parent_plant_pollen":
                value: Plant | None
                plant.parent_plant_pollen = value
            elif key == "filename_previewimage":
                value: str | None
                plant.filename_previewimage = value
            elif key == "taxon_id":
                value: int | None
                plant.taxon_id = value
            elif key == "taxon":
                value: Taxon | None
                plant.taxon = value
            else:
                raise UpdateNotImplemented(key)

        await self.session.flush()

    async def get_tag_by_tag_id(self, tag_id: int) -> Tag:
        query = select(Tag).where(Tag.id == tag_id).limit(1)  # noqa
        tag: Tag = (await self.session.scalars(query)).first()  # noqa
        if not tag:
            raise TagNotFound
        return tag

    async def update_tag(self, tag: Tag, updates: dict):
        if "text" in updates:
            tag.text = updates["text"]
        if "state" in updates:
            tag.state = updates["state"]
        if "plant_id" in updates:
            tag.plant_id = updates["plant_id"]

        await self.session.flush()

    async def remove_tag_from_plant(self, plant: Plant, tag: Tag):
        if tag not in plant.tags:
            raise TagNotAssignedToPlant(plant.id, tag.id)
        plant.tags.remove(tag)
        await self.session.delete(tag)
        await self.session.flush()

    async def delete_image_to_plant_association(
        self, link: ImageToPlantAssociation, plant: Plant = None
    ):
        if plant:
            plant.image_to_plant_associations.remove(link)
        await self.session.delete(link)
        await self.session.flush()

    async def get_all_plants_with_relationships_loaded(
        self, include_deleted=False
    ) -> list[Plant]:
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = select(Plant)

        if not include_deleted:
            # sqlite does not like "is None" and pylint doesn't like "== None"
            query = query.where(Plant.deleted.is_(False))

        # early-load all relationship tables for Plant model relevant for PResultsPlants
        # to save around 90% (postgres) of the time in comparison to lazy loading (80% for sqlite)
        query = query.options(
            selectinload(Plant.parent_plant),
            selectinload(Plant.parent_plant_pollen),
            selectinload(Plant.tags),
            selectinload(Plant.same_taxon_plants),
            selectinload(Plant.sibling_plants),
            selectinload(Plant.descendant_plants),
            selectinload(Plant.descendant_plants_pollen),
            # selectinload(Plant.descendant_plants_all),  # property
            selectinload(Plant.taxon),
            # selectinload(Plant.taxon_authors),  # property
            selectinload(Plant.events).selectinload(Event.soil),
            # selectinload(Plant.current_soil),  # property
            selectinload(Plant.images),
            # selectinload(Plant.latest_image),  # property
            # selectinload(Plant.image_to_plant_associations),  # not required
            # selectinload(Plant.florescences),  # not required
        )
        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

    async def get_all_plants_with_events_loaded(
        self, include_deleted=False
    ) -> list[Plant]:
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = select(Plant).options(
            selectinload(Plant.events).selectinload(Event.soil)
        )
        if not include_deleted:
            query = query.where(Plant.deleted.is_(False))

        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

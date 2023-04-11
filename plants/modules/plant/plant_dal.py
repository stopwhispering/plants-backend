from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from plants.exceptions import (
    CriterionNotImplementedError,
    PlantNotFoundError,
    TagNotAssignedToPlantError,
    TagNotFoundError,
    UpdateNotImplementedError,
)
from plants.modules.event.models import Event
from plants.modules.image.models import Image
from plants.modules.plant.models import Plant, Tag
from plants.shared.base_dal import BaseDAL

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PlantDAL(BaseDAL):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    @staticmethod
    def _add_eager_load_options(query: Select[Any]) -> Select[Any]:
        """Apply eager loading the query supplied; use only for single- or limited-
        number select queries to avoid performance issues."""
        return query.options(
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
            # selectinload(Plant.events).selectinload(Event.image_to_event_associations),
            selectinload(Plant.images).selectinload(Image.keywords),
            selectinload(Plant.florescences),
        )

    def expire(self, plant: Plant) -> None:
        self.session.expire(plant)

    async def by_id(self, plant_id: int, *, eager_load: bool = True) -> Plant:
        # noinspection PyTypeChecker
        query = (
            select(Plant)
            .where(Plant.id == plant_id)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .limit(1)
        )

        if eager_load:
            query = self._add_eager_load_options(query)

        plant: Plant | None = (await self.session.scalars(query)).first()
        if not plant:
            raise PlantNotFoundError(plant_id)
        return plant

    async def by_name(
        self,
        plant_name: str,
        *,
        eager_load: bool = True,
        only_active: bool = True,
        raise_not_found: bool = False,
    ) -> Plant | None:
        # noinspection PyTypeChecker
        query = (
            select(Plant)
            .where(Plant.plant_name == plant_name)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .limit(1)
        )

        if only_active:
            query = query.where(Plant.active)

        if eager_load:
            query = self._add_eager_load_options(query)

        plant: Plant | None = (await self.session.scalars(query)).first()

        if plant is None and raise_not_found:
            raise PlantNotFoundError(plant_name)

        return plant

    async def get_plant_by_criteria(self, criteria: dict[str, Any]) -> list[Plant]:
        query = select(Plant).where(Plant.deleted.is_(False))  # noqa: FBT003
        value: str
        for key, value in criteria.items():
            if "field_number" in key:
                query = query.filter(Plant.field_number == value)
            else:
                raise CriterionNotImplementedError(key)
        plants: list[Plant] = list((await self.session.scalars(query)).all())
        return plants

    async def get_name_by_id(self, plant_id: int) -> str:
        # noinspection PyTypeChecker
        query = (
            select(Plant.plant_name)
            .where(Plant.id == plant_id)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .limit(1)
        )
        plant_name: str | None = (await self.session.scalars(query)).first()
        if not plant_name:
            raise PlantNotFoundError(plant_id)
        return plant_name

    async def get_id_by_name(self, plant_name: str) -> int:
        # noinspection PyTypeChecker
        query = (
            select(Plant.id)
            .where(Plant.plant_name == plant_name)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .limit(1)
        )
        plant_id: int | None = (await self.session.scalars(query)).first()
        if not plant_id:
            raise PlantNotFoundError(plant_name)
        return plant_id

    async def get_count_plants_without_taxon(self) -> int:
        # noinspection PyTypeChecker
        query = (
            select(func.count())
            .select_from(Plant)
            .where(Plant.taxon_id.is_(None))
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .where(Plant.active)
        )
        count = (await self.session.scalars(query)).first()
        return cast(int, count)

    async def get_plants_ids_without_taxon(self) -> list[int]:
        # noinspection PyTypeChecker
        query = (
            select(Plant.id)
            .where(Plant.taxon_id.is_(None))
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .where(Plant.active)
        )
        plant_ids: list[int] = list((await self.session.scalars(query)).all())
        return plant_ids

    async def save_plant(self, plant: Plant) -> None:
        self.session.add(plant)
        await self.session.flush()

        # re-fetch plant to get eager load options
        await self.by_id(plant.id, eager_load=True)

    # async def create_empty_plant(self, plant_name: str) -> Plant:
    #     new_plant = Plant(plant_name=plant_name, deleted=False, active=True)
    #     self.session.add(new_plant)
    #     await self.session.flush()
    #     return await self.by_id(new_plant.id)  # adds eager load options

    async def create_plant(self, new_plant_data: dict[str, Any]) -> Plant:
        new_plant = Plant(**new_plant_data, deleted=False)
        self.session.add(new_plant)
        await self.session.flush()
        return await self.by_id(new_plant.id)

    async def create_tags(self, tags: list[Tag]) -> None:
        self.session.add_all(tags)
        await self.session.flush()

    async def get_all_plants_with_taxon(self) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .options(selectinload(Plant.taxon))
        )
        return list((await self.session.scalars(query)).all())

    async def set_count_stored_pollen_containers(self, plant: Plant, count: int) -> None:
        plant.count_stored_pollen_containers = count
        await self.session.flush()

    async def get_plants_without_pollen_containers(self) -> list[Plant]:
        # noinspection PyTypeChecker
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .where(Plant.active)
            .where(
                (Plant.count_stored_pollen_containers == 0)
                | Plant.count_stored_pollen_containers.is_(None)
            )
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .options(selectinload(Plant.taxon))
        )
        plants: list[Plant] = list((await self.session.scalars(query)).all())
        return plants

    async def get_plants_with_pollen_containers(self) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .where(Plant.count_stored_pollen_containers >= 1)
            .options(selectinload(Plant.taxon))
        )
        plants: list[Plant] = list((await self.session.scalars(query)).all())
        return plants

    async def get_children(
        self, seed_capsule_plant: Plant, pollen_donor_plant: Plant
    ) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .where(
                Plant.parent_plant_id == seed_capsule_plant.id,
                Plant.parent_plant_pollen_id == pollen_donor_plant.id,
            )
        )

        children: list[Plant] = list((await self.session.scalars(query)).all())
        return children

    async def get_children_by_ids(
        self, seed_capsule_plant_id: int, pollen_donor_plant_id: int
    ) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))  # noqa: FBT003
            .where(
                Plant.parent_plant_id == seed_capsule_plant_id,
                Plant.parent_plant_pollen_id == pollen_donor_plant_id,
            )
        )

        children: list[Plant] = list((await self.session.scalars(query)).all())
        return children

    async def exists(self, plant_name: str) -> bool:
        # noinspection PyTypeChecker
        query = select(Plant).where(Plant.plant_name == plant_name).limit(1)
        plant: Plant | None = (await self.session.scalars(query)).first()
        return plant is not None

    async def delete(self, plant: Plant) -> None:
        plant.deleted = True
        await self.session.flush()

    async def get_distinct_nurseries(self) -> list[str]:
        # noinspection PyTypeChecker
        query = (
            select(Plant.nursery_source)
            .where(Plant.nursery_source.isnot(None))
            .distinct(Plant.nursery_source)
        )
        nurseries: list[str] = list((await self.session.scalars(query)).all())
        return nurseries

    async def update(self, plant: Plant, updates: dict[str, Any]) -> None:  # noqa: C901 PLR0912
        for key, value in updates.items():
            if key == "plant_name":
                plant.plant_name = value
            elif key == "active":
                plant.active = updates["active"]
            elif key == "cancellation_reason":
                plant.cancellation_reason = value
            elif key == "cancellation_date":
                plant.cancellation_date = value
            elif key == "field_number":
                plant.field_number = value
            elif key == "geographic_origin":
                plant.geographic_origin = value
            elif key == "nursery_source":
                plant.nursery_source = value
            elif key == "propagation_type":
                plant.propagation_type = value
            elif key == "generation_notes":
                plant.generation_notes = value
            elif key == "plant_notes":
                plant.plant_notes = value
            elif key == "parent_plant_id":
                plant.parent_plant_id = value
            elif key == "parent_plant_pollen_id":
                plant.parent_plant_pollen_id = value
            elif key == "parent_plant_pollen":
                plant.parent_plant_pollen = value
            elif key == "preview_image_id":
                plant.preview_image_id = value
            elif key == "taxon_id":
                plant.taxon_id = value
            elif key == "taxon":
                plant.taxon = value
            else:
                raise UpdateNotImplementedError(key)

        await self.session.flush()

    async def get_tag_by_tag_id(self, tag_id: int) -> Tag:
        # noinspection PyTypeChecker
        query = select(Tag).where(Tag.id == tag_id).limit(1)
        tag: Tag | None = (await self.session.scalars(query)).first()
        if not tag:
            raise TagNotFoundError(tag_id)
        return tag

    async def update_tag(self, tag: Tag, updates: dict[str, Any]) -> None:
        if "text" in updates:
            tag.text = updates["text"]
        if "state" in updates:
            tag.state = updates["state"]
        if "plant_id" in updates:
            tag.plant_id = updates["plant_id"]

        await self.session.flush()

    async def remove_tag_from_plant(self, plant: Plant, tag: Tag) -> None:
        if tag not in plant.tags:
            raise TagNotAssignedToPlantError(plant.id, tag.id)
        plant.tags.remove(tag)
        await self.session.delete(tag)
        await self.session.flush()

    async def get_all_plants_with_relationships_loaded(
        self, *, include_deleted: bool = False
    ) -> list[Plant]:
        # filter out hidden ("deleted" in frontend but actually only flagged hidden)
        # plants
        query = select(Plant)

        if not include_deleted:
            # sqlite does not like "is None" and pylint doesn't like "== None"
            query = query.where(Plant.deleted.is_(False))  # noqa: FBT003

        # early-load all relationship tables for Plant model relevant for
        # PResultsPlants to save around 90% (postgres) of the time in comparison to
        # lazy loading (80% for sqlite)
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
        plants: list[Plant] = list((await self.session.scalars(query)).all())
        return plants

    async def get_all_plants_with_events_loaded(
        self, *, include_deleted: bool = False
    ) -> list[Plant]:
        # filter out hidden ("deleted" in frontend but actually only flagged hidden)
        # plants
        query = select(Plant).options(selectinload(Plant.events).selectinload(Event.soil))
        if not include_deleted:
            query = query.where(Plant.deleted.is_(False))  # noqa: FBT003

        plants: list[Plant] = list((await self.session.scalars(query)).all())
        return plants

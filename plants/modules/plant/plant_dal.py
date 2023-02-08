from sqlalchemy import select, Select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from plants.exceptions import PlantNotFound, TagNotFound, TagNotAssignedToPlant
from plants.modules.event.models import Event
from plants.modules.image.models import ImageToPlantAssociation
from plants.modules.plant.models import Plant, Tag
from plants.shared.base_dal import BaseDAL


class PlantDAL(BaseDAL):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    @staticmethod
    def _add_eager_load_options(query: Select) -> Select:
        query = query.options(
            selectinload(Plant.parent_plant),
            selectinload(Plant.parent_plant_pollen),
            selectinload(Plant.tags),
            selectinload(Plant.same_taxon_plants),
            selectinload(Plant.sibling_plants),
            selectinload(Plant.descendant_plants),
            selectinload(Plant.descendant_plants_pollen),
            selectinload(Plant.taxon),
            selectinload(Plant.events),
            selectinload(Plant.images),
            selectinload(Plant.property_values_plant),
            selectinload(Plant.florescences)
        )
        return query

    async def by_id(self, plant_id: int, eager_load=True) -> Plant:
        query = (select(Plant)
                 .where(Plant.id == plant_id)  # noqa
                 .where(Plant.deleted.is_(False))
                 .limit(1))

        if eager_load:
            query = self._add_eager_load_options(query)

        plant: Plant = (await self.session.scalars(query)).first()  # noqa
        if not plant:
            raise PlantNotFound(plant_id)
        return plant

    async def by_name(self, plant_name: str, eager_load=True, only_active=True) -> Plant:
        query = (select(Plant)
                 .where(Plant.plant_name == plant_name)  # noqa
                 .where(Plant.deleted.is_(False))
                 .limit(1))

        if only_active:
            query = query.where(Plant.active)

        if eager_load:
            query = self._add_eager_load_options(query)

        plant: Plant = (await self.session.scalars(query)).first()
        return plant

    async def get_plant_ids_by_taxon_id(self, taxon_id: int, eager_load=True, only_active=True) -> list[int]:
        query = (select(Plant.id)
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
        query = (select(Plant)  # .filter_by(**criteria)
                 .where(Plant.deleted.is_(False))
                 )
        for key, value in criteria.items():
            if 'field_number' in key:
                value: str
                query = query.filter(Plant.field_number == value)
            else:
                raise NotImplementedError(f'Criterion {key} not implemented')
        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

    async def get_name_by_id(self, plant_id: int) -> str:
        query = (select(Plant.plant_name)
                 .where(Plant.id == plant_id)  # noqa
                 .where(Plant.deleted.is_(False))
                 .limit(1))
        plant_name: str = (await self.session.scalars(query)).first()
        if not plant_name:
            raise PlantNotFound(plant_id)
        return plant_name

    async def get_id_by_name(self, plant_name: str) -> int:
        query = (select(Plant.id)
                 .where(Plant.plant_name == plant_name)  # noqa
                 .where(Plant.deleted.is_(False))
                 .limit(1))
        plant_id: int = (await self.session.scalars(query)).first()
        if not plant_id:
            raise PlantNotFound(plant_name)
        return plant_id

    async def get_count_plants_without_taxon(self) -> int:
        query = (select(func.count())
                 .select_from(Plant)
                 .where(Plant.taxon_id.is_(None))
                 .where(Plant.deleted.is_(False))
                 .where(Plant.active)
                 )
        count = (await self.session.scalar(query))
        return count

    async def get_plants_ids_without_taxon(self) -> list[int]:
        query = (select(Plant.id)
                 .where(Plant.taxon_id.is_(None))
                 .where(Plant.deleted.is_(False))
                 .where(Plant.active)
                 )
        plant_ids = (await self.session.scalar(query)).all()
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

    async def get_all_plants(self) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))
        )
        return (await self.session.scalars(query)).all()  # noqa

    async def set_count_stored_pollen_containers(self, plant: Plant, count: int):
        plant.count_stored_pollen_containers = count
        await self.session.flush()

    async def get_plants_without_pollen_containers(self) -> list[Plant]:
        query = (select(Plant)
                 .where(Plant.deleted.is_(False))
                 .where(Plant.active)
                 .where((Plant.count_stored_pollen_containers == 0) |
                        Plant.count_stored_pollen_containers.is_(None))
                 .where((Plant.deleted.is_(False))))
        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

    async def get_plants_with_pollen_containers(self) -> list[Plant]:
        query = (select(Plant)
                 .where(Plant.deleted.is_(False))
                 .where(Plant.count_stored_pollen_containers >= 1))
        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

    async def get_children(self, seed_capsule_plant: Plant, pollen_donor_plant: Plant) -> list[Plant]:
        query = (select(Plant)
                 .where(Plant.deleted.is_(False))
                 .where(Plant.parent_plant_id == seed_capsule_plant.id,
                        Plant.parent_plant_pollen_id == pollen_donor_plant.id))

        children: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return children

    async def get_children_by_ids(self, seed_capsule_plant_id: int, pollen_donor_plant_id: int) -> list[Plant]:
        query = (select(Plant)
                 .where(Plant.deleted.is_(False))
                 .where(Plant.parent_plant_id == seed_capsule_plant_id,
                        Plant.parent_plant_pollen_id == pollen_donor_plant_id))

        children: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return children

    async def exists(self, plant_name: str) -> bool:
        query = (select(Plant)
                 .where(Plant.plant_name == plant_name)  # noqa
                 .limit(1))
        plant: Plant = (await self.session.scalars(query)).first()
        return plant is not None

    async def delete(self, plant: Plant):
        plant.deleted = True
        await self.session.flush()

    async def get_distinct_nurseries(self) -> list[str]:
        query = (select(Plant.nursery_source)
                 .where(Plant.nursery_source.isnot(None))
                 .distinct(Plant.nursery_source))
        nurseries: list[str] = (await self.session.scalars(query)).all()  # noqa
        return nurseries

    async def update(self, plant: Plant, updates: dict):
        if 'plant_name' in updates:
            plant.plant_name = updates['plant_name']
        if 'active' in updates:
            plant.active = updates['active']
        if 'cancellation_reason' in updates:
            plant.cancellation_reason = updates['cancellation_reason']
        if 'cancellation_date' in updates:
            plant.cancellation_date = updates['cancellation_date']
        if 'field_number' in updates:
            plant.field_number = updates['field_number']
        if 'geographic_origin' in updates:
            plant.geographic_origin = updates['geographic_origin']
        if 'nursery_source' in updates:
            plant.nursery_source = updates['nursery_source']
        if 'propagation_type' in updates:
            plant.propagation_type = updates['propagation_type']
        if 'generation_notes' in updates:
            plant.generation_notes = updates['generation_notes']
        if 'plant_notes' in updates:
            plant.plant_notes = updates['plant_notes']
        if 'parent_plant_id' in updates:
            plant.parent_plant_id = updates['parent_plant_id']
        if 'parent_plant_pollen_id' in updates:
            plant.parent_plant_pollen_id = updates['parent_plant_pollen_id']
        if 'filename_previewimage' in updates:
            plant.filename_previewimage = updates['filename_previewimage']

        await self.session.flush()

    async def get_tag_by_tag_id(self, tag_id: int) -> Tag:
        query = (select(Tag)
                 .where(Tag.id == tag_id)  # noqa
                 .limit(1))
        tag: Tag = (await self.session.scalars(query)).first()  # noqa
        if not tag:
            raise TagNotFound
        return tag

    async def update_tag(self, tag: Tag, updates: dict):
        if 'text' in updates:
            tag.text = updates['text']
        if 'state' in updates:
            tag.state = updates['state']
        if 'plant_id' in updates:
            tag.plant_id = updates['plant_id']

        await self.session.flush()

    async def remove_tag_from_plant(self, plant: Plant, tag: Tag):
        if tag not in plant.tags:
            raise TagNotAssignedToPlant(plant.id, tag.id)
        plant.tags.remove(tag)
        await self.session.delete(tag)
        await self.session.flush()

    async def delete_image_to_plant_association(self, link: ImageToPlantAssociation, plant: Plant = None):
        if plant:
            plant.image_to_plant_associations.remove(link)
        await self.session.delete(link)
        await self.session.flush()

    async def get_all_plants_with_relationships_loaded(self, include_deleted=False) -> list[Plant]:
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

            # selectinload(Plant.property_values_plant),  # not required
            # selectinload(Plant.image_to_plant_associations),  # not required
            # selectinload(Plant.florescences),  # not required
        )
        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

    async def get_all_plants_with_events_loaded(self, include_deleted=False) -> list[Plant]:
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = (select(Plant)
                 .options(selectinload(Plant.events).selectinload(Event.soil))
                 )
        if not include_deleted:
            query = query.where(Plant.deleted.is_(False))

        plants: list[Plant] = (await self.session.scalars(query)).all()  # noqa
        return plants

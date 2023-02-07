from sqlalchemy import select
from sqlalchemy.orm import subqueryload, selectinload

from plants.exceptions import PlantNotFound, TagNotFound, TagNotAssignedToPlant
from plants.modules.event.models import Event
from plants.modules.image.models import ImageToPlantAssociation
from plants.modules.plant.models import Plant, Tag
from plants.shared.base_dal import BaseDAL


class PlantDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    def by_id(self, plant_id: int) -> Plant:
        query = (select(Plant)
                 .where(Plant.id == plant_id)  # noqa
                 .limit(1))
        plant: Plant = (self.session.scalars(query)).first()  # noqa
        if not plant:
            raise PlantNotFound(plant_id)
        return plant

    def by_name(self, plant_name: str) -> Plant:
        query = (select(Plant)
                 .where(Plant.plant_name == plant_name)  # noqa
                 .limit(1))
        plant: Plant = (self.session.scalars(query)).first()
        return plant

    def get_name_by_id(self, plant_id: int) -> str:
        query = (select(Plant.plant_name)
                 .where(Plant.id == plant_id)  # noqa
                 .limit(1))
        plant_name: str = (self.session.scalars(query)).first()
        if not plant_name:
            raise PlantNotFound(plant_id)
        return plant_name

    def get_id_by_name(self, plant_name: str) -> int:
        query = (select(Plant.id)
                 .where(Plant.plant_name == plant_name)  # noqa
                 .limit(1))
        plant_id: int = (self.session.scalars(query)).first()
        if not plant_id:
            raise PlantNotFound(plant_name)
        return plant_id

    def create_plant(self, plant: Plant):
        self.session.add(plant)
        self.session.flush()

    def create_empty_plant(self, plant_name: str) -> Plant:
        new_plant = Plant(plant_name=plant_name, deleted=False, active=True)
        self.session.add(new_plant)
        self.session.flush()
        return new_plant

    def create_tags(self, tags: list[Tag]):
        self.session.add_all(tags)
        self.session.flush()

    def get_all_plants(self) -> list[Plant]:
        query = (
            select(Plant)
            .where(Plant.deleted.is_(False))
        )
        return (self.session.scalars(query)).all()  # noqa

    def set_count_stored_pollen_containers(self, plant: Plant, count: int):
        plant.count_stored_pollen_containers = count
        self.session.flush()

    def get_plants_without_pollen_containers(self) -> list[Plant]:
        query = (select(Plant)
                 .where((Plant.count_stored_pollen_containers == 0) |
                        Plant.count_stored_pollen_containers.is_(None))
                 .where((Plant.deleted.is_(False))))
        plants: list[Plant] = (self.session.scalars(query)).all()  # noqa
        return plants

    def get_plants_with_pollen_containers(self) -> list[Plant]:
        query = (select(Plant)
                 .where(Plant.count_stored_pollen_containers >= 1))
        plants: list[Plant] = (self.session.scalars(query)).all()  # noqa
        return plants

    def get_children(self, seed_capsule_plant: Plant, pollen_donor_plant: Plant) -> list[Plant]:
        query = (select(Plant)
                 .where(Plant.parent_plant_id == seed_capsule_plant.id,
                        Plant.parent_plant_pollen_id == pollen_donor_plant.id))

        children: list[Plant] = (self.session.scalars(query)).all()  # noqa
        return children

    def exists(self, plant_name: str) -> bool:
        query = (select(Plant)
                 .where(Plant.plant_name == plant_name)  # noqa
                 .limit(1))
        plant: Plant = (self.session.scalars(query)).first()
        return plant is not None

    def delete(self, plant: Plant):
        plant.deleted = True
        self.session.flush()

    def update(self, plant: Plant, updates: dict):
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

        self.session.flush()

    def get_tag_by_tag_id(self, tag_id: int) -> Tag:
        query = (select(Tag)
                 .where(Tag.id == tag_id)  # noqa
                 .limit(1))
        tag: Tag = (self.session.scalars(query)).first()  # noqa
        if not tag:
            raise TagNotFound
        return tag

    def update_tag(self, tag: Tag, updates: dict):
        if 'text' in updates:
            tag.text = updates['text']
        if 'state' in updates:
            tag.state = updates['state']
        if 'plant_id' in updates:
            tag.plant_id = updates['plant_id']

        self.session.flush()

    def remove_tag_from_plant(self, plant: Plant, tag: Tag):
        if tag not in plant.tags:
            raise TagNotAssignedToPlant(plant.id, tag.id)
        plant.tags.remove(tag)
        self.session.delete(tag)
        self.session.flush()

    def delete_image_to_plant_association(self, link: ImageToPlantAssociation, plant: Plant = None):
        if plant:
            plant.image_to_plant_associations.remove(link)
        self.session.delete(link)
        self.session.flush()

    def get_all_plants_with_relationships_loaded(self, include_deleted=False) -> list[Plant]:
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = select(Plant)

        if not include_deleted:
            # sqlite does not like "is None" and pylint doesn't like "== None"
            query = query.where(Plant.deleted.is_(False))

        # early-load all relationship tables for Plant model relevant for PResultsPlants
        # to save around 90% (postgres) of the time in comparison to lazy loading (80% for sqlite)
        query = query.options(  # todo better use selectinload?
            subqueryload(Plant.parent_plant),
            subqueryload(Plant.parent_plant_pollen),

            subqueryload(Plant.tags),
            subqueryload(Plant.same_taxon_plants),
            subqueryload(Plant.sibling_plants),

            subqueryload(Plant.descendant_plants),
            subqueryload(Plant.descendant_plants_pollen),
            # subqueryload(Plant.descendant_plants_all),  # property

            subqueryload(Plant.taxon),
            # subqueryload(Plant.taxon_authors),  # property

            subqueryload(Plant.events),
            # subqueryload(Plant.current_soil),  # property

            subqueryload(Plant.images),
            # subqueryload(Plant.latest_image),  # property

            # subqueryload(Plant.property_values_plant),  # not required
            # subqueryload(Plant.image_to_plant_associations),  # not required
            # subqueryload(Plant.florescences),  # not required
        )
        plants: list[Plant] = (self.session.scalars(query)).all()  # noqa
        return plants

    def get_all_plants_with_events_loaded(self, include_deleted=False) -> list[Plant]:
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = (select(Plant)
                 .options(selectinload(Plant.events).selectinload(Event.soil))
                 )
        if not include_deleted:
            query = query.where(Plant.deleted.is_(False))

        plants: list[Plant] = (self.session.scalars(query)).all()  # noqa
        return plants

from sqlalchemy import select

from plants.modules.plant.models import Plant
from plants.shared.base_dal import BaseDAL


class PlantDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    def by_id(self, plant_id: int) -> Plant:
        query = (select(Plant)
                 .where(Plant.id == plant_id)  # noqa
                 .limit(1))
        plant: Plant = (self.session.scalars(query)).first()  # noqa
        return plant

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

from sqlalchemy import select

from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Pollination, COLORS_MAP_TO_RGB
from plants.shared.base_dal import BaseDAL


class PollinationDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    def create(self, pollination: Pollination):
        self.session.add(pollination)
        self.session.flush()

    def delete(self, pollination: Pollination):
        self.session.delete(pollination)
        self.session.flush()

    def update(self, pollination: Pollination, updates: dict):
        if 'pollen_type' in updates:
            pollination.pollen_type = updates['pollen_type']
        if 'location' in updates:
            pollination.location = updates['location']
        if 'pollination_timestamp' in updates:
            pollination.pollination_timestamp = updates['pollination_timestamp']
        if 'count' in updates:
            pollination.count = updates['count']
        if 'label_color' in updates:
            pollination.label_color = updates['label_color']
        if 'pollination_status' in updates:
            pollination.pollination_status = updates['pollination_status']
        if 'ongoing' in updates:
            pollination.ongoing = updates['ongoing']
        if 'harvest_date' in updates:
            pollination.harvest_date = updates['harvest_date']
        if 'seed_capsule_length' in updates:
            pollination.seed_capsule_length = updates['seed_capsule_length']
        if 'seed_capsule_width' in updates:
            pollination.seed_capsule_width = updates['seed_capsule_width']
        if 'seed_length' in updates:
            pollination.seed_length = updates['seed_length']
        if 'seed_width' in updates:
            pollination.seed_width = updates['seed_width']
        if 'seed_count' in updates:
            pollination.seed_count = updates['seed_count']
        if 'seed_capsule_description' in updates:
            pollination.seed_capsule_description = updates['seed_capsule_description']
        if 'seed_description' in updates:
            pollination.seed_description = updates['seed_description']
        if 'days_until_first_germination' in updates:
            pollination.days_until_first_germination = updates['days_until_first_germination']
        if 'first_seeds_sown' in updates:
            pollination.first_seeds_sown = updates['first_seeds_sown']
        if 'first_seeds_germinated' in updates:
            pollination.first_seeds_germinated = updates['first_seeds_germinated']
        if 'germination_rate' in updates:
            pollination.germination_rate = updates['germination_rate']
        if 'last_update_context' in updates:
            pollination.last_update_context = updates['last_update_context']

        self.session.flush()

    def get_ongoing_pollinations(self) -> list[Pollination]:
        query = select(Pollination) .where(Pollination.ongoing)
        pollinations: list[Pollination] = (self.session.scalars(query)).all()  # noqa
        return pollinations

    def get_available_colors_for_plant(self, plant: Plant):

        used_colors_query = (
            select(Pollination.label_color)
            .where(Pollination.seed_capsule_plant_id == plant.id,
                   Pollination.ongoing)
        )
        used_colors = (self.session.scalars(used_colors_query)).all()
        available_color_names = [c for c in COLORS_MAP_TO_RGB.keys() if c not in used_colors]
        available_colors_rgb = [COLORS_MAP_TO_RGB[c] for c in available_color_names]
        return available_colors_rgb

    def get_pollinations_with_filter(self, criteria: dict) -> list[Pollination]:
        query = select(Pollination)

        for key, value in criteria.items():
            if key == 'ongoing':
                value: bool
                query = query.where(Pollination.ongoing == value)
            elif key == 'seed_capsule_plant':
                value: Plant
                query = query.where(Pollination.seed_capsule_plant == value)
            elif key == 'pollen_donor_plant':
                value: Plant
                query = query.where(Pollination.pollen_donor_plant == value)
            elif key == 'seed_capsule_plant_id':
                value: int
                query = query.where(Pollination.seed_capsule_plant_id == value)
            elif key == 'label_color':
                value: str
                query = query.where(Pollination.label_color == value)
            else:
                raise NotImplemented(f'Unknown filter key: {key}')

        pollinations: list[Pollination] = (self.session.scalars(query)).all()  # noqa
        return pollinations

    def get_pollinations_by_plants(self, seed_capsule_plant: Plant, pollen_donor_plant: Plant) -> list[Pollination]:
        query = (select(Pollination)
                 .where(Pollination.seed_capsule_plant_id == seed_capsule_plant.id,
                        Pollination.pollen_donor_plant_id == pollen_donor_plant.id))

        pollinations: list[Pollination] = (self.session.scalars(query)).all()  # noqa
        return pollinations

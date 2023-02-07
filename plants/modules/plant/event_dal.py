from sqlalchemy import select

from plants.exceptions import EventNotFound, SoilNotFound
from plants.modules.event.models import Event, Soil, Observation, Pot
from plants.modules.image.models import Image, ImageToEventAssociation
from plants.modules.plant.models import Plant
from plants.shared.base_dal import BaseDAL


class EventDAL(BaseDAL):
    def __init__(self, session):
        super().__init__(session)

    def create_pot(self, pot: Pot):
        self.session.add(pot)
        self.session.flush()

    def create_observation(self, observation: Observation):
        self.session.add(observation)
        self.session.flush()

    def delete_observation(self, observation: Observation):
        self.session.delete(observation)
        self.session.flush()

    def create_soil(self, soil: Soil):
        self.session.add(soil)
        self.session.flush()

    def create_event(self, event: Event):
        self.session.add(event)
        self.session.flush()

    def create_events(self, events: list[Event]):
        self.session.add_all(events)
        self.session.flush()

    def add_images_to_event(self, event: Event, images: list[Image]):
        for image in images:
            event.images.append(image)
        self.session.flush()

    def get_all_soils(self) -> list[Soil]:
        query = select(Soil)
        soils: list[Soil] = (self.session.scalars(query)).all()  # noqa
        return soils

    def get_soil_by_id(self, soil_id: int) -> Soil:
        query = (select(Soil)
                 .where(Soil.id == soil_id)  # noqa
                 .limit(1))
        soil: Soil = (self.session.scalars(query)).first()
        if not soil:
            raise SoilNotFound(soil_id)
        return soil

    def update_soil(self, soil: Soil, updates: dict):
        for key, value in updates.items():
            if key == 'soil_name':
                value: str
                soil.soil_name = value
            elif key == 'description':
                value: str
                soil.description = value
            elif key == 'mix':
                value: str
                soil.mix = value
            else:
                raise NotImplemented(f'Invalid soil update key: {key}')

        self.session.flush()

    def get_soils_by_name(self, soil_name: str) -> list[Soil]:
        # todo: once we have made soil names unique, we can change this with singular version
        query = (select(Soil)
                 .where(Soil.soil_name == soil_name)  # noqa
                 )
        soils: list[Soil] = (self.session.scalars(query)).all()  # noqa
        return soils

    def get_event_by_plant_and_date(self, plant: Plant, event_date: str) -> Event:
        query = (select(Event)
                 .where(Event.plant_id == plant.id)
                 .where(Event.date == event_date)  # yyyy-mm-dd
                 .limit(1))
        event: Event = (self.session.scalars(query)).first()
        return event

    def by_id(self, event_id) -> Event:
        query = (select(Event)
                 .where(Event.id == event_id)  # noqa
                 .limit(1))
        event: Event = (self.session.scalars(query)).first()
        if not event:
            raise EventNotFound(event_id)
        return event

    def delete_image_to_event_associations(self, links: list[ImageToEventAssociation], event: Event = None):
        for link in links:
            if event:
                event.image_to_event_associations.remove(link)
            self.session.delete(link)
        self.session.flush()

    def delete_event(self, event: Event):
        self.session.delete(event)
        self.session.flush()

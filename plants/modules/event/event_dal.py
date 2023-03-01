from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from plants.exceptions import (
    EventNotFoundError,
    SoilNotFoundError,
    UpdateNotImplementedError,
)
from plants.modules.event.models import Event, Observation, Pot, Soil
from plants.shared.base_dal import BaseDAL

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from plants.modules.image.models import Image, ImageToEventAssociation
    from plants.modules.plant.models import Plant


class EventDAL(BaseDAL):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_events_by_plant(self, plant: Plant) -> list[Event]:
        """Read all events for supplied plant, including related images, observations,
        soils and pots."""
        query = (
            select(Event)
            .where(Event.plant_id == plant.id)
            .options(selectinload(Event.images))
            .options(selectinload(Event.observation))
            .options(selectinload(Event.soil))
            .options(selectinload(Event.pot))
        )
        events: list[Event] = list((await self.session.scalars(query)).all())  # noqa
        return events

    async def create_pot(self, pot: Pot) -> None:
        self.session.add(pot)
        await self.session.flush()

    async def create_observation(self, observation: Observation) -> None:
        self.session.add(observation)
        await self.session.flush()

    async def delete_observation(self, observation: Observation) -> None:
        await self.session.delete(observation)
        await self.session.flush()

    async def create_soil(self, soil: Soil) -> None:
        self.session.add(soil)
        await self.session.flush()

    async def create_event(self, event: Event) -> None:
        self.session.add(event)
        await self.session.flush()

    async def create_events(self, events: list[Event]) -> None:
        self.session.add_all(events)
        await self.session.flush()

    async def add_images_to_event(self, event: Event, images: list[Image]) -> None:
        for image in images:
            event.images.append(image)
        await self.session.flush()

    async def get_all_soils(self) -> list[Soil]:
        query = select(Soil)
        soils: list[Soil] = list((await self.session.scalars(query)).all())  # noqa
        return soils

    async def get_soil_by_id(self, soil_id: int) -> Soil:
        query = select(Soil).where(Soil.id == soil_id).limit(1)  # noqa
        soil: Soil | None = (await self.session.scalars(query)).first()
        if soil is None:
            raise SoilNotFoundError(soil_id)
        return soil

    async def update_soil(self, soil: Soil, updates: dict[str, Any]) -> None:
        for key, value in updates.items():
            if key == "soil_name":
                soil.soil_name = value
            elif key == "description":
                soil.description = value
            elif key == "mix":
                soil.mix = value
            else:
                raise UpdateNotImplementedError(key)

        await self.session.flush()

    async def get_soils_by_name(self, soil_name: str) -> list[Soil]:
        # todo: once we have made soil names unique, we can change this with singular
        #  version
        query = select(Soil).where(Soil.soil_name == soil_name)  # noqa
        soils: list[Soil] = list((await self.session.scalars(query)).all())  # noqa
        return soils

    async def get_event_by_plant_and_date(
        self, plant: Plant, event_date: str
    ) -> Event | None:
        query = (
            select(Event)
            .where(Event.plant_id == plant.id)
            .where(Event.date == event_date)  # yyyy-mm-dd
            .limit(1)
        )
        event: Event | None = (await self.session.scalars(query)).first()
        return event

    async def by_id(self, event_id: int) -> Event:
        query = (
            select(Event)
            .where(Event.id == event_id)  # noqa
            .options(selectinload(Event.images))
            .options(selectinload(Event.observation))
            .options(selectinload(Event.pot))
            .options(selectinload(Event.soil))
            .limit(1)
        )
        event: Event | None = (await self.session.scalars(query)).first()
        if not event:
            raise EventNotFoundError(event_id)
        return event

    async def delete_image_to_event_associations(
        self, links: list[ImageToEventAssociation], event: Event | None = None
    ) -> None:
        for link in links:
            if event:
                event.image_to_event_associations.remove(link)
            await self.session.delete(link)
        await self.session.flush()

    async def delete_event(self, event: Event) -> None:
        await self.session.delete(event)
        await self.session.flush()

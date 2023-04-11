from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from plants.modules.event.models import Event, Observation, Pot, Soil
from plants.modules.event.schemas import EventCreateUpdate, FRequestCreateOrUpdateEvent
from plants.modules.image.models import Image, ImageToEventAssociation

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from plants.modules.event.event_dal import EventDAL
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL


@pytest.mark.asyncio()
async def test_create_event(ac: AsyncClient, plant_valid_in_db):
    plant_id = plant_valid_in_db.id
    payload = {  # FRequestCreateOrUpdateEvent
        "plants_to_events": {
            plant_id: [
                {  # FCreateOrUpdateEvent
                    # 'id': ,
                    "plant_id": plant_id,
                    "date": "2023-01-01",
                    "event_notes": "     first event via api     ",
                    "images": [],
                    "observation": None,
                    "soil": None,
                    "pot": None,
                }
            ]
        }
    }

    # create the event via api
    response = await ac.post("/api/events/", json=payload)
    assert response.status_code == 200
    assert "added" in response.json().get("message").get("description").lower()

    # retrieve the event via api
    response = await ac.get("/api/events/" + str(plant_id))
    assert response.status_code == 200
    assert response.json().get("events")
    events = response.json().get("events")
    assert len(events) == 1
    event = events[0]
    assert event.get("plant_id") == plant_id
    assert event.get("event_notes") == "first event via api"
    assert event.get("date") == "2023-01-01"


@pytest.mark.asyncio()
async def test_delete_event(
    ac: AsyncClient,
    plant_in_db_with_image_and_events: Plant,
    plant_dal: PlantDAL,
    event_dal: EventDAL,
    test_db: AsyncSession,
):
    """Test deleting an event via api including cascade delete of related relations."""
    plant_id = plant_in_db_with_image_and_events.id
    event_id = plant_in_db_with_image_and_events.events[0].id
    soil_id = plant_in_db_with_image_and_events.events[0].soil.id
    pot_id = plant_in_db_with_image_and_events.events[0].pot.id
    observation_id = plant_in_db_with_image_and_events.events[0].observation.id

    payload = {"plants_to_events": {plant_id: []}}  # FRequestCreateOrUpdateEvent
    # update (including deletion) events via api
    response = await ac.post("/api/events/", json=payload)
    assert response.status_code == 200
    assert "deleted" in response.json().get("message").get("description").lower()

    # check event is deleted (in multiple ways...)
    plant_dal.expire(plant_in_db_with_image_and_events)
    plant = await plant_dal.by_id(plant_id)
    assert len(plant.events) == 0

    events = await event_dal.get_events_by_plant(plant=plant)
    assert len(events) == 0

    query = select(Event).where(Event.id == event_id)
    events = (await test_db.scalars(query)).all()
    assert len(events) == 0

    # check image assignment is deleted
    query = select(ImageToEventAssociation).where(ImageToEventAssociation.event_id == event_id)
    links = (await test_db.scalars(query)).all()
    assert len(links) == 0

    # check image itself is not deleted and still assigned to image
    query = select(Image).where(Image.id == plant.images[0].id)
    images = (await test_db.scalars(query)).all()
    assert len(images) == 1

    # check pot is deleted
    query = select(Pot).where(Pot.id == pot_id)
    pot = (await test_db.scalars(query)).first()
    assert not pot

    # check observation is deleted
    query = select(Observation).where(Observation.id == observation_id)
    observation = (await test_db.scalars(query)).first()
    assert not observation

    # check soil is not deleted
    query = select(Soil).where(Soil.id == soil_id)
    soil = (await test_db.scalars(query)).first()
    assert soil


@pytest.mark.asyncio()
async def test_update_event(
    ac: AsyncClient,
    plant_in_db_with_image_and_events: Plant,
    plant_dal: PlantDAL,
    event_dal: EventDAL,
    test_db: AsyncSession,
):
    """Test updating an event via api removing a hitherto existing observation, soil,
    pot, and image assignment."""
    event: Event = plant_in_db_with_image_and_events.events[0]
    plant_id = plant_in_db_with_image_and_events.id
    event_id = plant_in_db_with_image_and_events.events[0].id
    soil_id = plant_in_db_with_image_and_events.events[0].soil.id
    pot_id = plant_in_db_with_image_and_events.events[0].pot.id
    observation_id = plant_in_db_with_image_and_events.events[0].observation.id

    payload = FRequestCreateOrUpdateEvent(
        plants_to_events={
            plant_id: [
                EventCreateUpdate(
                    id=event.id,
                    plant_id=event.plant_id,
                    date=event.date,
                    event_notes="updated event",
                    images=[],
                    observation=None,
                    soil=None,
                    pot=None,
                )
            ]
        }
    )

    # update the event via api
    response = await ac.post("/api/events/", json=payload.dict())
    assert response.status_code == 200
    assert "deleted" in response.json().get("message").get("description").lower()

    test_db.expire(plant_in_db_with_image_and_events)
    test_db.expire(event)
    _ = await event_dal.by_id(event_id)
    _ = await plant_dal.by_id(plant_id)

    # check event has been updated
    assert event is not None
    assert event.plant_id == payload.plants_to_events[plant_id][0].plant_id
    assert event.date == payload.plants_to_events[plant_id][0].date
    assert event.event_notes == payload.plants_to_events[plant_id][0].event_notes
    assert len(event.images) == 0
    assert event.observation is None
    assert event.soil is None
    assert event.pot is None

    # check image assignment has been deleted
    query = select(ImageToEventAssociation).where(ImageToEventAssociation.event_id == event_id)
    links = (await test_db.scalars(query)).all()
    assert len(links) == 0

    # check image itself is not deleted and is still assigned to plant
    query = select(Image).where(Image.id == plant_in_db_with_image_and_events.images[0].id)
    images = (await test_db.scalars(query)).all()
    assert len(images) == 1

    # check pot is deleted
    query = select(Pot).where(Pot.id == pot_id)
    pot = (await test_db.scalars(query)).first()
    assert not pot

    # check observation is deleted
    query = select(Observation).where(Observation.id == observation_id)
    observation = (await test_db.scalars(query)).first()
    assert not observation

    # check soil is not deleted
    query = select(Soil).where(Soil.id == soil_id)
    soil = (await test_db.scalars(query)).first()
    assert soil

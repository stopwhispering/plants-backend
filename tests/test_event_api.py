from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from plants.modules.event.models import Event, Pot, Soil
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
    query = select(ImageToEventAssociation).where(
        ImageToEventAssociation.event_id == event_id
    )
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

    # check soil is not deleted
    query = select(Soil).where(Soil.id == soil_id)
    soil = (await test_db.scalars(query)).first()
    assert soil

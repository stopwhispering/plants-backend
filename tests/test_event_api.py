import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
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

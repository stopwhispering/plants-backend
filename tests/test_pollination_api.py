from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from plants.modules.pollination.schemas import (
    FRequestPollenContainers,
    PollenContainerCreateUpdate,
    PollinationCreate,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.pollination.models import Pollination
    from plants.modules.pollination.pollination_dal import PollinationDAL


@pytest.mark.asyncio()
async def test_create_pollination(
    ac: AsyncClient,
    plant_valid_with_active_florescence_in_db: Plant,
    valid_simple_plant_dict: dict[str, Any],
    plant_dal: PlantDAL,
    pollination_dal: PollinationDAL,
) -> None:
    """Includes creation of pollen container."""
    # via test client:
    # create plant 2 with pollen container for it
    payload = {"PlantsCollection": [valid_simple_plant_dict]}
    response = await ac.post("/api/plants/", json=payload)
    assert response.status_code == 200
    assert (p := response.json().get("plants")[0]) is not None
    payload_pc = FRequestPollenContainers(
        pollen_container_collection=[
            PollenContainerCreateUpdate(
                plant_id=p["id"],
                plant_name=p["plant_name"],
                genus="Aloe",
                count_stored_pollen_containers=4,
            )
        ]
    )
    response = await ac.post("/api/pollen_containers", json=payload_pc.dict())
    assert response.status_code == 200

    plant2: Plant | None = await plant_dal.by_name(p["plant_name"])
    assert plant2 is not None
    assert plant2.count_stored_pollen_containers == 4

    # create a florescence from active florescence and container
    # PollinationCreate
    payload_pollination = PollinationCreate(
        florescenceId=plant_valid_with_active_florescence_in_db.florescences[0].id,
        seed_capsule_plant_id=plant_valid_with_active_florescence_in_db.id,
        pollen_donor_plant_id=plant2.id,
        pollen_type="frozen",
        pollen_quality="good",
        pollinated_at="2022-11-16 12:06",
        label_color_rgb="#ff7c09",
        location="indoor",
        count=3,
    )
    response = await ac.post("/api/pollinations", json=payload_pollination.dict())
    assert response.status_code == 200
    pollinations = await pollination_dal.get_pollinations_by_plant_ids(
        plant_valid_with_active_florescence_in_db.id, plant2.id
    )
    assert len(pollinations) == 1
    pollination = pollinations[0]
    assert pollination.pollen_type == "frozen"
    assert pollination.location == "indoor"
    assert pollination.count == 3


@pytest.mark.asyncio()
async def test_update_pollination(
    ac: AsyncClient,
    test_db: AsyncSession,
    pollination_in_db: Pollination,
) -> None:
    """Update a pollination."""
    # get pollination via test client
    response = await ac.get("/api/ongoing_pollinations")
    assert response.status_code == 200
    resp = response.json()
    pollination = next(
        p
        for p in resp["ongoing_pollination_collection"]
        if p["id"] == pollination_in_db.id
    )

    # update attributes and send via test client
    pollination["location"] = "indoor"
    pollination["count"] = 2
    pollination["seed_capsule_length"] = 14.5
    pollination["label_color_rgb"] = "#ffffff"
    response = await ac.put(f"/api/pollinations/{pollination['id']}", json=pollination)
    assert response.status_code == 200

    # check if attributes have been updated
    await test_db.refresh(pollination_in_db)
    assert pollination_in_db.location == "indoor"
    assert pollination_in_db.count == 2
    assert pollination_in_db.seed_capsule_length == 14.5
    assert pollination_in_db.label_color == "white"

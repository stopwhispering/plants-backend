from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from plants.modules.event.schemas import SoilCreate, SoilUpdate

if TYPE_CHECKING:
    from httpx import AsyncClient

    from plants.modules.event.models import Soil


@pytest.mark.asyncio()
async def test_create_soil(ac: AsyncClient) -> None:
    payload = SoilCreate(
        soil_name="Coco Coir Test Bricks",
        mix="100% Coco Coir",
        description="Coco Coir Natural Fiber",
    )

    # create the soil via api
    response = await ac.post("/api/events/soils", json=payload.model_dump())
    assert response.status_code == 200

    # get soils via api and make sure the new soil is there
    response = await ac.get("/api/events/soils")
    assert response.status_code == 200
    resp = response.json()

    soils = resp.get("SoilsCollection")
    assert soils
    new_soil = next(s for s in soils if s.get("soil_name") == payload.soil_name)
    assert new_soil
    assert new_soil["soil_name"] == payload.soil_name
    assert new_soil["mix"] == payload.mix
    assert new_soil["description"] == payload.description


@pytest.mark.asyncio()
async def test_update_soil(ac: AsyncClient, soil_in_db: Soil) -> None:
    payload = SoilUpdate(
        id=soil_in_db.id,
        soil_name="Pumice with Perlite",
        mix="50% Pumice, 50% Perlite",
        description=None,
    )

    # create the soil via api
    response = await ac.put("/api/events/soils", json=payload.model_dump())
    assert response.status_code == 200

    # get soils via api and make sure the new soil is there
    response = await ac.get("/api/events/soils")
    assert response.status_code == 200
    resp = response.json()

    soils = resp.get("SoilsCollection")
    assert soils
    updated_soil = next(s for s in soils if s.get("id") == payload.id)
    assert updated_soil
    assert updated_soil["soil_name"] == payload.soil_name
    assert updated_soil["mix"] == payload.mix
    assert updated_soil["description"] == payload.description

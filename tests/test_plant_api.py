from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from plants.exceptions import PlantNotFoundError
from plants.modules.plant.schemas import PlantRenameRequest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.shared.history_dal import HistoryDAL


@pytest.mark.asyncio()
async def test_plants_query_empty(ac: AsyncClient) -> None:
    response = await ac.get("/api/plants/")
    assert response.status_code == 200
    assert response.json().get("action") == "Get plants"
    plants = response.json().get("PlantsCollection")
    assert len(plants) == 0


@pytest.mark.asyncio()
async def test_plants_query_all(ac: AsyncClient, plant_valid_in_db: Plant) -> None:
    response = await ac.get("/api/plants/")
    assert response.status_code == 200
    assert response.json().get("action") == "Get plants"
    plants = response.json().get("PlantsCollection")
    assert len(plants) == 1
    plant = plants[0]
    assert plant["plant_name"] == plant_valid_in_db.plant_name


@pytest.mark.asyncio()
async def test_plant_create_valid(ac: AsyncClient, valid_simple_plant_dict: dict[str, Any]) -> None:
    response = await ac.post("/api/plants/", json=valid_simple_plant_dict)
    assert response.status_code == 200
    assert response.json().get("plant") is not None

    # check that plant was created
    response = await ac.get("/api/plants/")
    assert response.status_code == 200
    plants = response.json().get("PlantsCollection")
    assert len(plants) == 1
    assert plants[0].get("plant_name") == "Aloe ferox"


@pytest.mark.asyncio()
async def test_plant_rename_valid(
    test_db: AsyncSession,
    ac: AsyncClient,
    plant_valid_in_db: Plant,
    plant_dal: PlantDAL,
    history_dal: HistoryDAL,
) -> None:
    old_plant_name = plant_valid_in_db.plant_name
    payload_ = PlantRenameRequest(
        new_plant_name="Aloe ferox var. ferox 'variegata'",
    )
    response = await ac.put(f"/api/plants/{plant_valid_in_db.id}/rename", json=payload_.dict())
    assert response.status_code == 200

    await test_db.refresh(plant_valid_in_db)
    assert not await plant_dal.exists(old_plant_name)
    assert plant_valid_in_db.plant_name == "Aloe ferox var. ferox 'variegata'"

    history_entries = await history_dal.get_all()
    history_entry = history_entries[0]
    assert history_entry.plant_id == plant_valid_in_db.id
    assert history_entry.description.startswith("Renamed")


@pytest.mark.asyncio()
async def test_plant_rename_target_exists(
    ac: AsyncClient,
    plant_valid_in_db: Plant,
    plant_valid_with_active_florescence_in_db: Plant,
    history_dal: HistoryDAL,
) -> None:
    payload = {
        "new_plant_name": plant_valid_with_active_florescence_in_db.plant_name,
    }
    response = await ac.put(f"/api/plants/{plant_valid_in_db.id}/rename", json=payload)
    assert 400 <= response.status_code < 500
    assert "already exists" in response.json().get("detail")

    history_entries = await history_dal.get_all()
    assert len(history_entries) == 0


@pytest.mark.asyncio()
async def test_plant_rename_source_not_exists(ac: AsyncClient) -> None:
    payload = {
        "new_plant_name": "Aloe redundata",
    }
    response = await ac.put("/api/plants/11551/rename", json=payload)
    assert 400 <= response.status_code < 500
    assert "Plant" in str(response.json())
    assert "not found" in str(response.json())


@pytest.mark.asyncio()
async def test_propose_subsequent_plant_name(ac: AsyncClient) -> None:
    original_plant_name = "Aloe ferox"
    response = await ac.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert response.json().get("subsequent_plant_name") == "Aloe ferox II"

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana II"
    response = await ac.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert (
        response.json().get("subsequent_plant_name")
        == "× Aloe rauhii 'Demi' × Gasteria batesiana III"
    )

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana V"
    response = await ac.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert (
        response.json().get("subsequent_plant_name")
        == "× Aloe rauhii 'Demi' × Gasteria batesiana VI"
    )

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana VIII"
    response = await ac.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert (
        response.json().get("subsequent_plant_name")
        == "× Aloe rauhii 'Demi' × Gasteria batesiana IX"
    )


@pytest.mark.asyncio()
async def test_clone_plant(
    ac: AsyncClient, plant_dal: PlantDAL, valid_plant_in_db_with_image: Plant
) -> None:
    response = await ac.post(
        f"/api/plants/{valid_plant_in_db_with_image.id}/clone?" f"plant_name_clone=Aloe vera clone"
    )
    assert response.status_code == 201
    resp = response.json()

    assert resp["plant"]["plant_name"] == "Aloe vera clone"
    assert resp["plant"]["id"] is not None

    clone = await plant_dal.by_id(resp["plant"]["id"])
    assert clone.active is True
    assert clone.botanical_name == valid_plant_in_db_with_image.botanical_name
    assert clone.field_number == valid_plant_in_db_with_image.field_number
    assert clone.florescences == []
    assert clone.full_botanical_html_name == (valid_plant_in_db_with_image.full_botanical_html_name)
    assert clone.propagation_type == valid_plant_in_db_with_image.propagation_type
    assert clone.taxon is valid_plant_in_db_with_image.taxon
    assert {t.text for t in clone.tags} == {t.text for t in valid_plant_in_db_with_image.tags}


@pytest.mark.asyncio()
async def test_clone_plant_bad_name(
    ac: AsyncClient,
    valid_plant_in_db_with_image: Plant,
    another_valid_plant_in_db: Plant,
) -> None:
    """Test cloning a plant and give clone a name that already exists.

    Expecting failure.
    """

    response = await ac.post(
        f"/api/plants/{valid_plant_in_db_with_image.id}/clone?"
        f"plant_name_clone={another_valid_plant_in_db.plant_name}"
    )
    assert response.status_code == 400
    resp = response.json()
    assert "exist" in resp["detail"]


@pytest.mark.asyncio()
async def test_delete_plant(
    ac: AsyncClient,
    test_db: AsyncSession,
    plant_dal: PlantDAL,
    valid_plant_in_db_with_image: Plant,
) -> None:
    plant_id = valid_plant_in_db_with_image.id

    response = await ac.delete(f"/api/plants/{valid_plant_in_db_with_image.id}")
    assert response.status_code == 200

    # check that the plant is deleted
    with pytest.raises(PlantNotFoundError):
        await plant_dal.by_id(plant_id)

    await test_db.refresh(valid_plant_in_db_with_image)
    assert valid_plant_in_db_with_image.deleted is True


@pytest.mark.asyncio()
async def test_rename_plant(
    ac: AsyncClient, test_db: AsyncSession, valid_plant_in_db_with_image: Plant
) -> None:
    """Test renaming a plant."""
    payload = PlantRenameRequest(new_plant_name="Aloe barbadensis")
    response = await ac.put(
        f"/api/plants/{valid_plant_in_db_with_image.id}/rename", json=payload.dict()
    )
    assert response.status_code == 200

    # check that the plant is renamed
    await test_db.refresh(valid_plant_in_db_with_image)
    assert valid_plant_in_db_with_image.plant_name == "Aloe barbadensis"


@pytest.mark.asyncio()
async def test_rename_plant_invalid(
    ac: AsyncClient,
    test_db: AsyncSession,
    valid_plant_in_db_with_image: Plant,
    another_valid_plant_in_db: Plant,
) -> None:
    """Test renaming a plant to a name that already exists."""
    old_name = valid_plant_in_db_with_image.plant_name
    new_name = another_valid_plant_in_db.plant_name
    payload = PlantRenameRequest(new_plant_name=new_name)
    response = await ac.put(
        f"/api/plants/{valid_plant_in_db_with_image.id}/rename", json=payload.dict()
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

    # check that the plant is not renamed
    await test_db.refresh(valid_plant_in_db_with_image)
    assert valid_plant_in_db_with_image.plant_name == old_name

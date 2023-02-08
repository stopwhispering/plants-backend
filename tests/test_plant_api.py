import pytest
from httpx import AsyncClient

from plants.shared.history_dal import HistoryDAL
from plants.modules.plant.models import Plant


@pytest.mark.asyncio
async def test_plants_query_empty(ac: AsyncClient):
    response = await ac.get("/api/plants/")
    assert response.status_code == 200
    assert response.json().get('action') == 'Get plants'
    plants = response.json().get('PlantsCollection')
    assert len(plants) == 0


@pytest.mark.asyncio
async def test_plants_query_all(ac: AsyncClient, plant_valid_in_db: Plant):
    response = await ac.get("/api/plants/")
    assert response.status_code == 200
    assert response.json().get('action') == 'Get plants'
    plants = response.json().get('PlantsCollection')
    assert len(plants) == 1
    plant = plants[0]
    assert plant['plant_name'] == plant_valid_in_db.plant_name


@pytest.mark.asyncio
async def test_plant_create_valid(ac: AsyncClient, valid_simple_plant_dict):
    payload = {'PlantsCollection': [valid_simple_plant_dict]}
    response = await ac.post("/api/plants/", json=payload)
    assert response.status_code == 200
    assert response.json().get('plants')[0] is not None

    # check that plant was created
    response = await ac.get("/api/plants/")
    assert response.status_code == 200
    plants = response.json().get('PlantsCollection')
    assert len(plants) == 1
    assert plants[0].get('plant_name') == 'Aloe ferox'


@pytest.mark.asyncio
async def test_plant_rename_valid(db, ac: AsyncClient, plant_valid_in_db, plant_dal, history_dal):
    payload = {
        'plant_id': plant_valid_in_db.id,
        'old_plant_name': plant_valid_in_db.plant_name,
        'new_plant_name': "Aloe ferox var. ferox 'variegata'"}
    response = await ac.put("/api/plants/", json=payload)
    assert response.status_code == 200

    await db.refresh(plant_valid_in_db)
    assert not await plant_dal.exists(payload['old_plant_name'])
    assert plant_valid_in_db.plant_name == "Aloe ferox var. ferox 'variegata'"

    history_entries = await history_dal.get_all()
    history_entry = history_entries[0]
    assert history_entry.plant_id == plant_valid_in_db.id
    assert history_entry.description.startswith('Renamed')


@pytest.mark.asyncio
async def test_plant_rename_target_exists(ac: AsyncClient,
                                          plant_valid_in_db,
                                          plant_valid_with_active_florescence_in_db,
                                          history_dal: HistoryDAL):
    payload = {
        'plant_id': plant_valid_in_db.id,
        'old_plant_name': plant_valid_in_db.plant_name,
        'new_plant_name': plant_valid_with_active_florescence_in_db.plant_name
    }
    response = await ac.put("/api/plants/", json=payload)
    assert 400 <= response.status_code < 500
    assert 'already exists' in response.json().get('detail')

    history_entries = await history_dal.get_all()
    assert len(history_entries) == 0


@pytest.mark.asyncio
async def test_plant_rename_source_not_exists(ac: AsyncClient):
    payload = {
        'plant_id': 11551,
        'old_plant_name': 'Aloe nonexista',
        'new_plant_name': 'Aloe redundata'
    }
    response = await ac.put("/api/plants/", json=payload)
    assert 400 <= response.status_code < 500
    assert 'Plant' in str(response.json()) and 'not found' in str(response.json())


@pytest.mark.asyncio
async def test_propose_subsequent_plant_name(ac: AsyncClient):
    original_plant_name = 'Aloe ferox'
    response = await ac.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert response.json().get('subsequent_plant_name') == 'Aloe ferox II'

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana II"
    response = await ac.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert response.json().get('subsequent_plant_name') == "× Aloe rauhii 'Demi' × Gasteria batesiana III"

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana V"
    response = await ac.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert response.json().get('subsequent_plant_name') == "× Aloe rauhii 'Demi' × Gasteria batesiana VI"

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana VIII"
    response = await ac.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert response.json().get('subsequent_plant_name') == "× Aloe rauhii 'Demi' × Gasteria batesiana IX"

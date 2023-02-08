import pytest
from httpx import AsyncClient

from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.models import Florescence, FlorescenceStatus


@pytest.mark.asyncio
async def test_florescence_create_valid(ac: AsyncClient, valid_simple_plant_dict, valid_florescence_dict):
    # create plant
    payload = {'PlantsCollection': [valid_simple_plant_dict]}
    response = await ac.post("/api/plants/", json=payload)
    assert response.status_code == 200
    assert response.json().get('plants')[0] is not None

    # create florescence for plant
    response = await ac.post("/api/active_florescences", json=valid_florescence_dict)
    assert response.status_code == 200

    # get florescences
    response = await ac.get("/api/active_florescences")
    assert response.status_code == 200
    active_florescence = response.json().get('activeFlorescenceCollection')[0]
    assert active_florescence.get('comment') == 'large & new'  # first space has been trimmed

    # update florescence (valid)
    payload = {
        'id': active_florescence.get('id'),
        'plant_id': active_florescence.get('id'),
        'florescence_status': 'flowering',
        'perianth_length': 1.3,
        'perianth_diameter': 0.8,
        'flower_color': '#F2F600',  # will be lower-cased
        'flower_color_second': '#dddd00',
        'flower_colors_differentiation': "ovary_mouth",  # ["ovary_mouth", "top_bottom"]
        'stigma_position': "deeply_inserted",
    }
    response = await ac.put(f"/api/active_florescences/{active_florescence.get('id')}", json=payload)
    assert response.status_code == 200

    # get florescences
    response = await ac.get("/api/active_florescences")
    assert response.status_code == 200
    assert len(response.json().get('activeFlorescenceCollection')) == 1
    active_florescence = response.json().get('activeFlorescenceCollection')[0]
    assert active_florescence.get('perianth_length') == 1.3
    assert active_florescence.get('perianth_diameter') == 0.8
    assert active_florescence.get('flower_color') == '#f2f600'  # lower-case
    assert active_florescence.get('flower_color_second') == '#dddd00'
    assert active_florescence.get('flower_colors_differentiation') == "ovary_mouth"
    assert active_florescence.get('stigma_position') == "deeply_inserted"

    # update florescence (invalid): flower_colors_differentiation only allowed if flower_color_second is set
    del payload['flower_color_second']
    response = await ac.put(f"/api/active_florescences/{active_florescence.get('id')}", json=payload)
    assert response.status_code == 400

    # update florescence (invalid): uniform differentiation but second color set
    payload['flower_color_second'] = '#dddd00'
    payload['flower_colors_differentiation'] = "uniform"
    response = await ac.put(f"/api/active_florescences/{active_florescence.get('id')}", json=payload)
    assert response.status_code == 400

    # update florescence (invalid): second same as first color (must be different)
    payload['flower_color_second'] = '#F2F600'
    payload['flower_colors_differentiation'] = "ovary_mouth"
    response = await ac.put(f"/api/active_florescences/{active_florescence.get('id')}", json=payload)
    assert response.status_code == 400

    # must be unchanged
    response = await ac.get("/api/active_florescences")
    assert response.status_code == 200
    active_florescence = response.json().get('activeFlorescenceCollection')[0]
    assert active_florescence.get('flower_color_second') == '#dddd00'


@pytest.mark.asyncio
async def test_create_and_abort_florescence(db, ac: AsyncClient, plant_valid_in_db: Plant, plant_dal: PlantDAL):
    # FRequestNewFlorescence
    payload = {
        "plant_id": plant_valid_in_db.id,
        "florescence_status": "inflorescence_appeared",
        "inflorescence_appearance_date": "2022-11-16",
        "comment": "    large & new "
    }
    response = await ac.post("/api/active_florescences", json=payload)
    assert response.status_code == 200
    plant_valid_in_db = await plant_dal.by_id(plant_valid_in_db.id)
    assert len(plant_valid_in_db.florescences) == 1
    florescence_in_db: Florescence = plant_valid_in_db.florescences[0]
    assert florescence_in_db.florescence_status == FlorescenceStatus.INFLORESCENCE_APPEARED

    # FRequestEditedFlorescence
    payload = {
        "id": florescence_in_db.id,
        "plant_id": plant_valid_in_db.id,
        "florescence_status": "doing_great",  # invalid
    }
    response = await ac.put(f"/api/active_florescences/{florescence_in_db.id}", json=payload)
    assert 400 <= response.status_code <= 499
    await db.refresh(florescence_in_db)  # reloads (only) attributes, no relationships are set to not loaded
    assert florescence_in_db.florescence_status == FlorescenceStatus.INFLORESCENCE_APPEARED

    payload['florescence_status'] = "aborted"
    response = await ac.put(f"/api/active_florescences/{florescence_in_db.id}", json=payload)
    assert response.status_code == 200
    await db.refresh(florescence_in_db)
    assert florescence_in_db.florescence_status == FlorescenceStatus.ABORTED
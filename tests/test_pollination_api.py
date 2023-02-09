import pytest
from httpx import AsyncClient

from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.pollination_dal import PollinationDAL


@pytest.mark.asyncio
async def test_florescence_create_valid(ac: AsyncClient,
                                        plant_valid_with_active_florescence_in_db: Plant,
                                        valid_simple_plant_dict,
                                        plant_dal: PlantDAL,
                                        pollination_dal: PollinationDAL):
    """includes creation of pollen container"""
    # via test client:
    # create plant 2 with pollen container for it
    payload = {'PlantsCollection': [valid_simple_plant_dict]}
    response = await ac.post("/api/plants/", json=payload)
    assert response.status_code == 200
    assert (p := response.json().get('plants')[0]) is not None
    payload = {'pollenContainerCollection': [{'plant_id': p['id'],
                                              'plant_name': p['plant_name'],
                                              'genus': 'Aloe',
                                              'count_stored_pollen_containers': 4,
                                              }]}
    response = await ac.post("/api/pollen_containers", json=payload)
    assert response.status_code == 200
    # plant2: Plant = Plant.by_name(p['plant_name'], db)
    plant2: Plant = await plant_dal.by_name(p['plant_name'])
    assert plant2.count_stored_pollen_containers == 4

    # create a florescence from active florescence and container
    payload = {
        'florescenceId': plant_valid_with_active_florescence_in_db.florescences[0].id,
        'seed_capsule_plant_id': plant_valid_with_active_florescence_in_db.id,
        'pollen_donor_plant_id': plant2.id,
        'pollen_type': 'frozen',
        'pollination_timestamp': '2022-11-16 12:06',
        'label_color_rgb': '#ff7c09',
        'location': 'indoor',
        'count': 3
    }
    response = await ac.post("/api/pollinations", json=payload)
    assert response.status_code == 200
    pollinations = await pollination_dal.get_pollinations_by_plant_ids(plant_valid_with_active_florescence_in_db.id,
                                                                       plant2.id)
    assert len(pollinations) == 1
    pollination = pollinations[0]
    assert pollination.pollen_type == 'frozen'
    assert pollination.location == 'indoor'
    assert pollination.count == 3

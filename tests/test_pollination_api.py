from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Pollination


def test_florescence_create_valid(db, test_client, plant_valid_with_active_florescence, valid_simple_plant_dict,
                                  plant_dal):
    """includes creation of pollen container"""
    # via orm:
    # create plant 1 with active florescence
    db.add(plant_valid_with_active_florescence)
    db.commit()

    # via testclient:
    # create plant 2 with pollen container for it
    payload = {'PlantsCollection': [valid_simple_plant_dict]}
    response = test_client.post("/api/plants/", json=payload)
    assert response.status_code == 200
    assert (p := response.json().get('plants')[0]) is not None
    payload = {'pollenContainerCollection': [{'plant_id': p['id'],
                                              'plant_name': p['plant_name'],
                                              'genus': 'Aloe',
                                              'count_stored_pollen_containers': 4,
                                              }]}
    response = test_client.post("/api/pollen_containers/", json=payload)
    assert response.status_code == 200
    # plant2: Plant = Plant.by_name(p['plant_name'], db)
    plant2: Plant = plant_dal.by_name(p['plant_name'])
    assert plant2.count_stored_pollen_containers == 4

    # create a florescence from active florescence and container
    payload = {
        'florescenceId': plant_valid_with_active_florescence.florescences[0].id,
        'seedCapsulePlantId': plant_valid_with_active_florescence.id,
        'pollenDonorPlantId': plant2.id,
        'pollenType': 'frozen',
        'pollinationTimestamp': '2022-11-16 12:06',
        'labelColorRgb': '#ff7c09',
        'location': 'indoor',
        'count': 3
    }
    response = test_client.post("/api/pollinations/", json=payload)
    assert response.status_code == 200
    pollination = db.query(Pollination).filter(
        Pollination.seed_capsule_plant_id == plant_valid_with_active_florescence.id,
        Pollination.pollen_donor_plant_id == plant2.id).first()
    assert pollination is not None
    assert pollination.pollen_type == 'frozen'
    assert pollination.location == 'indoor'
    assert pollination.count == 3

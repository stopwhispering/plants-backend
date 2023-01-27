from plants.modules.plant.models import Plant


def test_plants_query_empty(db, test_client):
    response = test_client.get("/api/plants/")
    assert response.status_code == 200
    assert response.json().get('action') == 'Get plants'
    plants = response.json().get('PlantsCollection')
    assert len(plants) == 0


def test_plant_create_valid(db, test_client, valid_simple_plant_dict):
    payload = {'PlantsCollection': [valid_simple_plant_dict]}
    response = test_client.post("/api/plants/", json=payload)
    assert response.status_code == 200
    assert response.json().get('plants')[0] is not None

    # check that plant was created
    response = test_client.get("/api/plants/")
    assert response.status_code == 200
    plants = response.json().get('PlantsCollection')
    assert len(plants) == 1
    assert plants[0].get('plant_name') == 'Aloe ferox'


def test_plant_rename_valid(db, test_client, valid_simple_plant_dict):
    payload = {'PlantsCollection': [valid_simple_plant_dict]}
    response = test_client.post("/api/plants/", json=payload)
    assert response.status_code == 200
    assert response.json().get('plants')[0] is not None

    payload = {'OldPlantName': 'Aloe ferox',
               'NewPlantName': 'Aloe ferox var. ferox'}
    response = test_client.put("/api/plants/", json=payload)
    assert response.status_code == 200

    assert db.query(Plant).filter(Plant.plant_name == 'Aloe ferox').first() is None
    assert db.query(Plant).filter(Plant.plant_name == 'Aloe ferox var. ferox').first() is not None


def test_plant_rename_target_exists(db, test_client, valid_simple_plant_dict, valid_another_simple_plant_dict):
    payload = {'PlantsCollection': [valid_simple_plant_dict]}  # 'Aloe ferox'
    response = test_client.post("/api/plants/", json=payload)
    assert response.status_code == 200

    payload = {'PlantsCollection': [valid_another_simple_plant_dict]}  # 'Gasteria bicolor var. fallax'
    response = test_client.post("/api/plants/", json=payload)
    assert response.status_code == 200

    payload = {'OldPlantName': 'Aloe ferox',
               'NewPlantName': 'Gasteria bicolor var. fallax'}
    response = test_client.put("/api/plants/", json=payload)
    assert response.status_code != 200
    assert response.json().get('detail').get('message').startswith('Plant already exists')


def test_plant_rename_source_not_exists(db, test_client, valid_simple_plant_dict, valid_another_simple_plant_dict):
    payload = {'PlantsCollection': [valid_simple_plant_dict]}  # 'Aloe ferox'
    response = test_client.post("/api/plants/", json=payload)
    assert response.status_code == 200

    payload = {'PlantsCollection': [valid_another_simple_plant_dict]}  # 'Gasteria bicolor var. fallax'
    response = test_client.post("/api/plants/", json=payload)
    assert response.status_code == 200

    payload = {'OldPlantName': 'Aloe vera',
               'NewPlantName': 'Aloe redundata'}
    response = test_client.put("/api/plants/", json=payload)
    assert response.status_code != 200
    assert response.json().get('detail').get('message').startswith("Can't find plant")

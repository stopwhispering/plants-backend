from plants.modules.plant.models import Plant
from plants.shared.history_models import History


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


def test_plant_rename_valid(db, test_client, plant_valid_in_db):
    # payload = {'PlantsCollection': [valid_simple_plant_dict]}
    # response = test_client.post("/api/plants/", json=payload)
    # assert response.status_code == 200
    # assert response.json().get('plants')[0] is not None
    #
    payload = {
        'plant_id': plant_valid_in_db.id,
        'old_plant_name': plant_valid_in_db.plant_name,
        'new_plant_name': "Aloe ferox var. ferox 'variegata'"}
    response = test_client.put("/api/plants/", json=payload)
    assert response.status_code == 200

    db.expire_all()  # refresh orm objects
    assert db.query(Plant).filter(Plant.plant_name == payload['old_plant_name']).first() is None
    assert plant_valid_in_db.plant_name == "Aloe ferox var. ferox 'variegata'"

    history_entry = db.query(History).first()
    assert history_entry.plant_id == plant_valid_in_db.id
    assert history_entry.description.startswith('Renamed')


# def test_plant_rename_target_exists(db, test_client, valid_simple_plant_dict, valid_another_simple_plant_dict):
def test_plant_rename_target_exists(db, test_client, plant_valid_in_db, plant_valid_with_active_florescence_in_db):
    payload = {
        'plant_id': plant_valid_in_db.id,
        'old_plant_name': plant_valid_in_db.plant_name,
        'new_plant_name': plant_valid_with_active_florescence_in_db.plant_name
    }
    response = test_client.put("/api/plants/", json=payload)
    assert 400 <= response.status_code < 500
    assert 'already exists' in response.json().get('detail')

    history_entry = db.query(History).first()
    assert history_entry is None or not history_entry.description.startswith('Renamed')


def test_plant_rename_source_not_exists(db, test_client):
    payload = {
        'plant_id': 11551,
        'old_plant_name': 'Aloe nonexista',
        'new_plant_name': 'Aloe redundata'
    }
    response = test_client.put("/api/plants/", json=payload)
    assert 400 <= response.status_code < 500
    assert 'Plant' in str(response.json()) and 'not found' in str(response.json())


def test_propose_subsequent_plant_name(test_client):
    original_plant_name = 'Aloe ferox'
    response = test_client.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}")
    assert response.status_code == 200
    assert response.json().get('subsequent_plant_name') == 'Aloe ferox II'

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana II"
    response = test_client.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}/")
    assert response.status_code == 200
    assert response.json().get('subsequent_plant_name') == "× Aloe rauhii 'Demi' × Gasteria batesiana III"

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana V"
    response = test_client.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}/")
    assert response.status_code == 200
    assert response.json().get('subsequent_plant_name') == "× Aloe rauhii 'Demi' × Gasteria batesiana VI"

    original_plant_name = "× Aloe rauhii 'Demi' × Gasteria batesiana VIII"
    response = test_client.post(f"/api/plants/propose_subsequent_plant_name/{original_plant_name}/")
    assert response.status_code == 200
    assert response.json().get('subsequent_plant_name') == "× Aloe rauhii 'Demi' × Gasteria batesiana IX"


def test_florescence_create_valid(db, test_client, valid_simple_plant_dict, valid_florescence_dict):
    # create plant
    payload = {'PlantsCollection': [valid_simple_plant_dict]}
    response = test_client.post("/api/plants/", json=payload)
    assert response.status_code == 200
    assert response.json().get('plants')[0] is not None

    # create florescence for plant
    response = test_client.post("/api/active_florescences/", json=valid_florescence_dict)
    assert response.status_code == 200

    # get florescences
    response = test_client.get("/api/active_florescences/")
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
    response = test_client.put(f"/api/active_florescences/{active_florescence.get('id')}", json=payload)
    assert response.status_code == 200

    # get florescences
    response = test_client.get("/api/active_florescences/")
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
    response = test_client.put(f"/api/active_florescences/{active_florescence.get('id')}", json=payload)
    assert response.status_code == 400

    # update florescence (invalid): uniform differentiation but second color set
    payload['flower_color_second'] = '#dddd00'
    payload['flower_colors_differentiation'] = "uniform"
    response = test_client.put(f"/api/active_florescences/{active_florescence.get('id')}", json=payload)
    assert response.status_code == 400

    # update florescence (invalid): second same as first color (must be different)
    payload['flower_color_second'] = '#F2F600'
    payload['flower_colors_differentiation'] = "ovary_mouth"
    response = test_client.put(f"/api/active_florescences/{active_florescence.get('id')}", json=payload)
    assert response.status_code == 400

    # must be unchanged
    response = test_client.get("/api/active_florescences/")
    assert response.status_code == 200
    active_florescence = response.json().get('activeFlorescenceCollection')[0]
    assert active_florescence.get('flower_color_second') == '#dddd00'

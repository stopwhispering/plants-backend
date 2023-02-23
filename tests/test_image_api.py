import os

import pytest
from httpx import AsyncClient

import json

from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
import plants as plants_package


@pytest.mark.asyncio
async def test_untagged_images_empty(ac: AsyncClient):
    response = await ac.get("/api/images/untagged/")
    assert response.status_code == 200
    assert response.json().get('message').get('message') == 'Returned 0 images.'


@pytest.mark.asyncio
async def test_upload_images(ac: AsyncClient,
                             plant_valid_in_db: Plant,
                             image_dal: ImageDAL,
                             ):
    # we need to wrap files and additional data in a way that matches the UI5 file uploader (which is a kind of odd way)
    files = [("files[]", ("demo_image1.jpg", open(r"./static/demo_image1.jpg", "rb"))),
             ("files[]", ("demo_image2.jpg", open(r"./static/demo_image2.jpg", "rb")))]

    payload = {  # FImageUploadedMetadata
        "files-data": json.dumps({
            "plants": (plant_valid_in_db.id,),
            "keywords": ('test_upload',)
        })
    }

    response = await ac.post("/api/images/", files=files, data=payload)
    assert response.status_code == 200

    assert 'saved' in response.json()['message']['message'].lower()
    resp_image_1 = response.json()['images'][0]
    resp_image_2 = response.json()['images'][1]
    assert len(resp_image_1['plants']) == 1
    assert resp_image_1['plants'][0]['plant_name'] == 'Aloe Vera'
    image_1_id = resp_image_1['id']
    image_2_id = resp_image_2['id']

    image_1_db = await image_dal.by_id(image_1_id)
    image_2_db = await image_dal.by_id(image_2_id)
    assert image_1_db is not None
    assert image_2_db is not None
    assert len(image_1_db.plants) == 1
    assert image_1_db.plants[0].plant_name == 'Aloe Vera'
    assert len(image_2_db.keywords) == 1
    assert image_2_db.keywords[0].keyword == 'test_upload'

    # test files uploaded (and maybe autoresized)
    file_paths = list(plants_package.settings.paths.path_original_photos_uploaded.glob('*'))
    file_names = [f.name for f in file_paths]
    assert ('demo_image1.jpg' in file_names or 'demo_image1_autoresized.jpg' in file_names)
    assert ('demo_image2.jpg' in file_names or 'demo_image2_autoresized.jpg' in file_names)

    # thumbnails generated
    for size in plants_package.settings.images.sizes:
        size: tuple[int, int]
        for full_filename in file_names:
            stub = full_filename.replace('.jpg', '').replace('.jpeg', '')
            filename = f"{stub}.{size[0]}_{size[1]}.jpg"
            path = plants_package.settings.paths.path_generated_thumbnails.joinpath(filename)
            assert path.is_file()


@pytest.mark.asyncio
async def test_upload_image_for_plant(ac: AsyncClient,
                                      plant_valid_in_db: Plant,
                                      image_dal: ImageDAL,
                                      plant_dal: PlantDAL,
                                      ):
    # we need to wrap files and additional data in a way that matches the UI5 file uploader (which is a kind of odd way)
    print(os.getcwd())
    files = [
        ("files[]", ("demo_image_plant.jpg", open(r"./static/demo_image_plant.jpg", "rb"))),  # todo config
    ]

    response = await ac.post(f"/api/plants/{plant_valid_in_db.id}/images/", files=files)
    assert response.status_code == 200
    image_id = response.json()['images'][0]['id']

    image_db = await image_dal.by_id(image_id)
    assert image_db is not None
    assert len(image_db.plants) == 1
    assert image_db.plants[0].id == plant_valid_in_db.id
    assert image_db.plants[0] is plant_valid_in_db
    assert len(image_db.keywords) == 0

    # test files uploaded (and maybe autoresized)
    file_paths = list(plants_package.settings.paths.path_original_photos_uploaded.glob('*'))
    file_names = [f.name for f in file_paths]
    assert ('demo_image_plant.jpg' in file_names or 'demo_image_plant_autoresized.jpg' in file_names)
    if 'demo_image_plant_autoresized.jpg' in file_names:
        full_filename = 'demo_image_plant_autoresized.jpg'
    else:
        full_filename = 'demo_image_plant.jpg'

    # thumbnails generated
    for size in plants_package.settings.images.sizes:
        size: tuple[int, int]
        stub = full_filename.replace('.jpg', '').replace('.jpeg', '')
        filename = f"{stub}.{size[0]}_{size[1]}.jpg"
        path = plants_package.settings.paths.path_generated_thumbnails.joinpath(filename)
        assert path.is_file()

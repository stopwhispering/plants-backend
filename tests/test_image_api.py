from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PIL import Image

import plants as plants_package
from plants import settings
from plants.exceptions import ImageNotFoundError
from plants.modules.event.schemas import FImageDelete, FImagesToDelete

if TYPE_CHECKING:
    from httpx import AsyncClient

    from plants.modules.image.image_dal import ImageDAL
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL


@pytest.mark.asyncio()
async def test_untagged_images_empty(ac: AsyncClient) -> None:
    response = await ac.get("/api/images/untagged/")
    assert response.status_code == 200
    assert response.json().get("message").get("message") == "Returned 0 images."


@pytest.mark.asyncio()
async def test_upload_images(
    ac: AsyncClient,
    plant_valid_in_db: Plant,
    image_dal: ImageDAL,
) -> None:
    # we need to wrap files and additional data in a way that matches the UI5 file
    # uploader (which is a kind of odd way)
    path1 = Path(__file__).resolve().parent.joinpath("./static/demo_image1.jpg")
    path2 = Path(__file__).resolve().parent.joinpath("./static/demo_image2.jpg")
    files = [
        ("files[]", ("demo_image1.jpg", path1.open("rb"))),
        ("files[]", ("demo_image2.jpg", path2.open("rb"))),
    ]

    payload = {  # FImageUploadedMetadata
        "files-data": json.dumps(
            {"plants": (plant_valid_in_db.id,), "keywords": ("test_upload",)}
        )
    }

    response = await ac.post("/api/images/", files=files, data=payload)
    assert response.status_code == 200

    assert "saved" in response.json()["message"]["message"].lower()
    resp_image_1 = response.json()["images"][0]
    resp_image_2 = response.json()["images"][1]
    assert len(resp_image_1["plants"]) == 1
    assert resp_image_1["plants"][0]["plant_name"] == "Aloe Vera"
    image_1_id = resp_image_1["id"]
    image_2_id = resp_image_2["id"]

    image_1_db = await image_dal.by_id(image_1_id)
    image_2_db = await image_dal.by_id(image_2_id)
    assert image_1_db is not None
    assert image_2_db is not None
    assert len(image_1_db.plants) == 1
    assert image_1_db.plants[0].plant_name == "Aloe Vera"
    assert len(image_2_db.keywords) == 1
    assert image_2_db.keywords[0].keyword == "test_upload"

    # test files uploaded (and maybe autoresized)
    file_paths = list(
        plants_package.settings.paths.path_original_photos_uploaded.glob("*")
    )
    file_names = [f.name for f in file_paths]
    assert (
        "demo_image1.jpg" in file_names or "demo_image1_autoresized.jpg" in file_names
    )
    assert (
        "demo_image2.jpg" in file_names or "demo_image2_autoresized.jpg" in file_names
    )

    # thumbnails generated
    size: tuple[int, int]
    for size in plants_package.settings.images.sizes:
        for full_filename in file_names:
            stub = full_filename.replace(".jpg", "").replace(".jpeg", "")
            filename = f"{stub}.{size[0]}_{size[1]}.jpg"
            path = plants_package.settings.paths.path_generated_thumbnails.joinpath(
                filename
            )
            assert path.is_file()


@pytest.mark.asyncio()
async def test_upload_image_for_plant(
    ac: AsyncClient,
    plant_valid_in_db: Plant,
    image_dal: ImageDAL,
) -> None:
    # we need to wrap files and additional data in a way that matches the UI5 file
    # uploader (which is a kind of odd way)
    path = Path(__file__).resolve().parent.joinpath("./static/demo_image_plant.jpg")
    files = [
        (
            "files[]",
            ("demo_image_plant.jpg", path.open("rb")),
        ),
    ]

    response = await ac.post(f"/api/plants/{plant_valid_in_db.id}/images/", files=files)
    assert response.status_code == 200
    image_id = response.json()["images"][0]["id"]

    image_db = await image_dal.by_id(image_id)
    assert image_db is not None
    assert len(image_db.plants) == 1
    assert image_db.plants[0].id == plant_valid_in_db.id
    assert image_db.plants[0] is plant_valid_in_db
    assert len(image_db.keywords) == 0

    # test files uploaded (and maybe autoresized)
    file_paths = list(
        plants_package.settings.paths.path_original_photos_uploaded.glob("*")
    )
    file_names = [f.name for f in file_paths]
    assert (
        "demo_image_plant.jpg" in file_names
        or "demo_image_plant_autoresized.jpg" in file_names
    )
    if "demo_image_plant_autoresized.jpg" in file_names:
        full_filename = "demo_image_plant_autoresized.jpg"
    else:
        full_filename = "demo_image_plant.jpg"

    # thumbnails generated
    size: tuple[int, int]
    for size in plants_package.settings.images.sizes:
        stub = full_filename.replace(".jpg", "").replace(".jpeg", "")
        filename = f"{stub}.{size[0]}_{size[1]}.jpg"
        path = plants_package.settings.paths.path_generated_thumbnails.joinpath(
            filename
        )
        assert path.is_file()


@pytest.mark.asyncio()
async def test_update_image(
    ac: AsyncClient,
    valid_plant_in_db_with_image: Plant,
) -> None:
    """The actual update has been done in the fixture, we just assert that it worked."""
    response = await ac.get(f"/api/plants/{valid_plant_in_db_with_image.id}/images/")
    assert response.status_code == 200
    images = response.json()
    image = images[0]
    assert image["description"] == "some description"
    assert len(image["keywords"]) == 2
    keywords = [kw["keyword"] for kw in image["keywords"]]
    assert "flower" in keywords
    assert "new leaf" in keywords


@pytest.mark.asyncio()
async def test_delete_image(
    ac: AsyncClient,
    valid_plant_in_db_with_image: Plant,
    image_dal: ImageDAL,
    plant_dal: PlantDAL,
) -> None:
    """Delete an image that is assigned to a plant.

    Make sure that it is deleted from db, file system, and plant.
    """
    payload = FImagesToDelete(
        images=[
            FImageDelete(
                id=valid_plant_in_db_with_image.images[0].id,
                filename=valid_plant_in_db_with_image.images[0].filename,
            )
        ]
    )
    image_filename = valid_plant_in_db_with_image.images[0].filename
    # unfortunately, HTTPX does not support DELETE with body, so we generate
    # the request manually
    response = await ac.request(
        url="/api/images/", method="DELETE", json=payload.dict()
    )
    assert response.status_code == 200

    # check that image file is deleted
    file_paths = list(
        plants_package.settings.paths.path_original_photos_uploaded.glob("*")
    )
    file_names = {f.name for f in file_paths}
    assert image_filename not in file_names

    # check that image is deleted from db
    with pytest.raises(ImageNotFoundError):
        await image_dal.by_id(payload.images[0].id)

    # check that image is deleted from plant
    plant_id = valid_plant_in_db_with_image.id
    # force reload from db
    plant_dal.expire(valid_plant_in_db_with_image)
    plant_in_db = await plant_dal.by_id(plant_id)
    assert len(plant_in_db.images) == 0


@pytest.mark.asyncio()
async def test_get_image_in_different_sizes(
    ac: AsyncClient,
    valid_plant_in_db_with_image: Plant,
) -> None:
    image_id: int = valid_plant_in_db_with_image.images[0].id

    # get image in original size
    response = await ac.get(url=f"/api/image/{image_id}")
    assert response.status_code == 200
    image_response = Image.open(BytesIO(response.content))
    assert image_response.format == "JPEG"

    # get image in different sizes
    for size in settings.images.sizes:
        params: dict[str, str] = {
            "width": str(size[0]),
            "height": str(size[1]),
        }
        response = await ac.get(url=f"/api/image/{image_id}", params=params)
        assert response.status_code == 200
        image_response = Image.open(BytesIO(response.content))
        assert image_response.format == "JPEG"
        assert image_response.width == size[0] or image_response.height == size[1]

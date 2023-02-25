import asyncio
import json
import shutil
from datetime import date
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

import plants as plants_package
from plants.extensions import orm
from plants.extensions.logging import LogLevel
from plants.extensions.orm import Base, init_orm
from plants.modules.event.event_dal import EventDAL
from plants.modules.image.image_dal import ImageDAL
from plants.modules.image.models import Image
from plants.modules.plant.enums import FBPropagationType
from plants.modules.plant.models import Plant, Tag
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.models import Florescence, Pollination
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.taxon.models import Taxon
from plants.shared.api_utils import date_hook
from plants.shared.history_dal import HistoryDAL
from tests.config_test import create_tables_if_required, generate_db_url

TEST_DB_NAME = "test_plants"


# redefine the event_loop fixture to have a session scope,
# see https://github.com/tortoise/tortoise-orm/issues/638
@pytest.fixture(scope="session")
def event_loop():
    # return asyncio.get_event_loop()
    return asyncio.new_event_loop()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db() -> None:
    """Setup test database: Create & Reset database to initial state; Create all
    database tables as declared in SQLAlchemy models;"""
    # PostGres does not allow to create/drop databases in a transaction, therefore we
    # need a separate engine for that that has isolation_level='AUTOCOMMIT'
    # (unlike default 'READ COMMITTED')
    engine_for_db_setup = create_async_engine(
        generate_db_url(TEST_DB_NAME), isolation_level="AUTOCOMMIT"
    )

    # AsyncConnection.begin() actually AsyncConnection.connect() and yields the
    # AsyncConnection after starting the AsyncTransaction with AsyncConnection.begin()
    # The AsyncTransaction is commited or rolled back when the AsyncConnection is
    # closed,
    # i.e. after the asynccontextmanager exits.
    async with engine_for_db_setup.begin() as setup_connection:
        setup_connection: AsyncConnection

        await setup_connection.execute(text("DROP SCHEMA public CASCADE;"))
        await setup_connection.execute(text("CREATE SCHEMA public;"))

        Base.metadata.bind = setup_connection
        await init_orm(engine=setup_connection.engine)
        await create_tables_if_required(engine=setup_connection.engine)


def _reset_paths():
    # cf. parse_settings()
    for path in [
        plants_package.settings.paths.path_deleted_photos,
        plants_package.settings.paths.path_generated_thumbnails,
        plants_package.settings.paths.path_generated_thumbnails_taxon,
        plants_package.settings.paths.path_original_photos_uploaded,
        plants_package.settings.paths.path_pickled_ml_models,
    ]:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)


@pytest_asyncio.fixture(scope="function")
async def test_db(request) -> AsyncSession:  # noqa
    """Wrapper fot get_db that truncates tables after each test function run."""
    # db = await anext(get_db())
    db = orm.SessionFactory.create_session()

    try:
        yield db

    finally:
        # if db.is_active:
        # we need to execute single statements with an async connection
        conn = await db.connection()
        await conn.execute(text("DELETE FROM history;"))
        await conn.execute(text("DELETE FROM tags;"))
        await conn.execute(text("DELETE FROM pollination;"))
        await conn.execute(text("DELETE FROM florescence;"))
        await conn.execute(text("DELETE FROM image_keywords;"))
        await conn.execute(text("DELETE FROM image_to_plant_association;"))
        await conn.execute(text("DELETE FROM image;"))
        await conn.execute(text("DELETE FROM soil;"))
        await conn.execute(text("DELETE FROM pot;"))
        await conn.execute(text("DELETE FROM event;"))
        await conn.execute(text("DELETE FROM plants;"))
        await conn.execute(text("DELETE FROM distribution;"))
        await conn.execute(text("DELETE FROM taxon;"))
        # TRUNCATE table_a, table_b, …, table_z;
        await conn.commit()
        await conn.close()

        _reset_paths()


@pytest_asyncio.fixture(scope="function")
async def plant_valid(request) -> Plant:  # noqa
    plant = Plant(
        plant_name="Aloe Vera",
        field_number="A100",
        active=True,
        deleted=False,
        nursery_source="Worldwide Cactus",
        propagation_type=FBPropagationType.LEAF_CUTTING,
        filename_previewimage="somefile.jpg",
        tags=[
            Tag(text="new", state="Information"),
            Tag(text="wow", state="Information"),
        ],
    )
    return plant


@pytest_asyncio.fixture(scope="function")
async def plant_valid_in_db(test_db, plant_valid, taxon_in_db: Taxon) -> Plant:
    """create a valid plant in the database and return it."""
    plant_valid.taxon = taxon_in_db
    test_db.add(plant_valid)
    await test_db.commit()
    return plant_valid


@pytest_asyncio.fixture(scope="function")
async def valid_plant_in_db_with_image(ac, test_db, plant_valid_in_db) -> Plant:
    """upload an image for the plant and return it."""
    path = Path(__file__).resolve().parent.joinpath("./static/demo_valid_plant.jpg")
    files = [
        (
            "files[]",
            ("demo_image_plant.jpg", open(path, "rb")),
        )
    ]
    response = await ac.post(f"/api/plants/{plant_valid_in_db.id}/images/", files=files)
    assert response.status_code == 200
    resp = response.json()

    # also set some keywords and set a description
    modified_image = resp["images"][0].copy()
    modified_image["keywords"] = [{"keyword": "flower"}, {"keyword": "new leaf"}]
    modified_image["description"] = " some description  "  # will be stripped
    payload = {"ImagesCollection": [modified_image]}  # BImageUpdated
    await ac.put("/api/images/", json=payload)

    # reload to have image reations available
    q = (
        select(Plant)
        .where(Plant.id == plant_valid_in_db.id)
        .options(
            selectinload(Plant.images).selectinload(Image.keywords),
            selectinload(Plant.image_to_plant_associations),
        )
    )
    plant_valid_in_db = (await test_db.scalars(q)).first()
    yield plant_valid_in_db


@pytest_asyncio.fixture(scope="function")
async def plant_valid_with_active_florescence() -> Plant:
    plant = Plant(
        plant_name="Gasteria obtusa",
        active=True,
        deleted=False,
        tags=[Tag(text="thirsty", state="Information")],
        florescences=[
            Florescence(
                inflorescence_appearance_date=date(2023, 1, 1),  # '2023-01-01',
                branches_count=1,
                flowers_count=12,
                florescence_status="flowering",
                creation_context="manual",
            )
        ],
    )

    yield plant


@pytest_asyncio.fixture(scope="function")
async def plant_valid_with_active_florescence_in_db(
    test_db: AsyncSession, plant_valid_with_active_florescence: Plant
) -> Plant:
    test_db.add(plant_valid_with_active_florescence)
    await test_db.commit()
    return plant_valid_with_active_florescence


@pytest_asyncio.fixture(scope="session")
def app() -> FastAPI:
    """only here do we import the main module.

    to avoid the regular database being initialized, we override the database url with a
    test database url we also override the get_db dependency called by most api
    endpoints to return a test database session
    """
    plants_package.local_config.connection_string = generate_db_url(TEST_DB_NAME)

    plants_package.local_config.log_settings.log_level_console = LogLevel.WARNING
    plants_package.local_config.log_settings.log_level_file = LogLevel.NONE

    plants_package.settings.paths.path_photos = Path("/common/plants_test/photos")
    plants_package.settings.paths.path_deleted_photos = Path(
        "/common/plants_test/photos/deleted"
    )
    plants_package.settings.paths.path_pickled_ml_models = Path(
        "/common/plants_test/pickled"
    )

    _reset_paths()

    from plants.main import app as main_app

    return main_app


@pytest_asyncio.fixture(scope="session")
async def ac(app) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://localhost") as ac:
        yield ac


@pytest.fixture(scope="function")
def valid_simple_plant_dict() -> dict:
    new_plant = {
        "plant_name": "Aloe ferox",
        "active": True,
        # 'descendant_plants_all': [],
        # 'sibling_plants': [],
        # 'same_taxon_plants': [],
        "tags": [],
    }
    return new_plant


@pytest_asyncio.fixture(scope="function")
async def another_valid_plant_in_db(test_db) -> Plant:
    """create a valid plant in the database and return it."""
    new_plant_data = {
        "plant_name": "Gasteria bicolor var. fallax",
        "active": True,
        "deleted": False,
        "tags": [],
    }
    new_plant = Plant(**new_plant_data)
    test_db.add(new_plant)
    await test_db.commit()
    return new_plant


@pytest.fixture(scope="function")
def valid_florescence_dict() -> dict:
    valid_florescence = {
        "plant_id": 1,
        "florescence_status": "flowering",
        "inflorescence_appearance_date": "2022-11-16",
        "comment": " large & new",
    }
    return valid_florescence


@pytest.fixture(scope="function")
def plant_dal(test_db: AsyncSession) -> PlantDAL:
    """"""
    yield PlantDAL(test_db)


@pytest.fixture(scope="function")
def pollination_dal(test_db: AsyncSession) -> PollinationDAL:
    """"""
    yield PollinationDAL(test_db)


@pytest.fixture(scope="function")
def history_dal(test_db: AsyncSession) -> HistoryDAL:
    """"""
    yield HistoryDAL(test_db)


@pytest.fixture(scope="function")
def event_dal(test_db: AsyncSession) -> EventDAL:
    """"""
    yield EventDAL(test_db)


@pytest.fixture(scope="function")
def image_dal(test_db: AsyncSession) -> ImageDAL:
    """"""
    yield ImageDAL(test_db)


@pytest_asyncio.fixture(scope="function")
async def taxon_in_db(request, test_db) -> Taxon:  # noqa
    """Create a valid taxon in the db and return it."""
    path = Path(__file__).resolve().parent.joinpath("./data/demo_taxon.json")
    with open(path, "r") as f:
        taxon_dict = json.load(f)

    taxon = Taxon(**taxon_dict)

    test_db.add(taxon)
    await test_db.commit()

    yield taxon


@pytest_asyncio.fixture(scope="function")
async def florescence_dict() -> dict:
    """Read florescence dict from json; has no plant attached."""
    path_florescence = (
        Path(__file__).resolve().parent.joinpath("./data/demo_florescence.json")
    )
    with open(path_florescence, "r") as f:
        florescence_dict = json.load(f, object_hook=date_hook)
    return florescence_dict


@pytest_asyncio.fixture(scope="function")
async def pollination_dict() -> dict:
    """Read pollination dict from json; has no florescence, seed_capsule_plant, or
    pollen_donor_plant attached."""
    path_pollination = (
        Path(__file__).resolve().parent.joinpath("./data/demo_pollination.json")
    )
    with open(path_pollination, "r") as f:
        pollination_dict = json.load(f, object_hook=date_hook)
    return pollination_dict


@pytest_asyncio.fixture(scope="function")
async def pollination_in_db(
    test_db,
    florescence_dict: dict,
    pollination_dict: dict,
    plant_valid_in_db: Plant,
    another_valid_plant_in_db: Plant,
) -> Pollination:  # noqa
    """Create a valid pollination in the db and return it."""
    florescence = Florescence(**florescence_dict, plant=plant_valid_in_db)
    pollination = Pollination(
        **pollination_dict,
        florescence=florescence,
        seed_capsule_plant=plant_valid_in_db,
        pollen_donor_plant=another_valid_plant_in_db,
    )

    test_db.add(pollination)
    await test_db.commit()

    yield pollination

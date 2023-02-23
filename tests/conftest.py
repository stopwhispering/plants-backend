import asyncio
import shutil
from datetime import date
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

import plants as plants_package
from plants.extensions import orm
from plants.extensions.logging import LogLevel
from plants.extensions.orm import Base, init_orm
from plants.modules.event.event_dal import EventDAL
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.enums import FBPropagationType
from plants.modules.plant.models import Plant, Tag
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.models import Florescence
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.shared.history_dal import HistoryDAL
from tests.config_test import create_tables_if_required, generate_db_url

TEST_DB_NAME = "test_plants"


# redefine the event_loop fixture to have a session scope,
# see https://github.com/tortoise/tortoise-orm/issues/638
@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


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
        # TRUNCATE table_a, table_b, …, table_z;
        await conn.commit()
        await conn.close()


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


# @pytest.fixture(scope="function")
# def property_dal(test_db: AsyncSession) -> PropertyDAL:
#     """
#     """
#     yield PropertyDAL(test_db)


@pytest_asyncio.fixture(scope="function")
async def plant_valid(request) -> Plant:  # noqa
    plant = Plant(
        plant_name="Aloe Vera",
        field_number="A100",
        active=True,
        deleted=False,
        nursery_source="Some Nursery",
        propagation_type=FBPropagationType.LEAF_CUTTING,
        filename_previewimage="somefile.jpg",
        tags=[
            Tag(text="new", state="Information"),
            Tag(text="wow", state="Information"),
        ],
    )
    return plant


@pytest_asyncio.fixture(scope="function")
async def plant_valid_in_db(test_db, plant_valid) -> Plant:
    test_db.add(plant_valid)
    await test_db.commit()
    return plant_valid


@pytest_asyncio.fixture(scope="function")
async def plant_valid_with_active_florescence(test_db) -> Plant:
    # query = (select(Plant)
    #          .where(Plant.plant_name == 'Gasteria obtusa')  # noqa
    #          # .limit(1)
    #          )
    # plant_todo_delme: Plant = (await test_db.scalars(query)).first()

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

    query = (
        select(Plant).where(Plant.plant_name == "Gasteria obtusa")  # noqa
        # .limit(1)
    )
    (await test_db.scalars(query)).first()

    return plant


@pytest_asyncio.fixture(scope="function")
async def plant_valid_with_active_florescence_in_db(
    test_db: AsyncSession, plant_valid_with_active_florescence: Plant
) -> Plant:
    # query = (select(Plant)
    #          .where(Plant.plant_name == plant_valid_with_active_florescence.plant_name)  # noqa
    #          .limit(1))
    # plant_todo_delme: Plant = (await test_db.scalars(query)).first()

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


@pytest.fixture(scope="function")
def valid_another_simple_plant_dict() -> dict:
    new_plant = {
        "plant_name": "Gasteria bicolor var. fallax",
        "active": True,
        "descendant_plants_all": [],
        "sibling_plants": [],
        "same_taxon_plants": [],
        "tags": [],
    }
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

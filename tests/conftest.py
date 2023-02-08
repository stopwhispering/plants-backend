import asyncio
from datetime import date

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine, AsyncSession


from plants.dependencies import get_db
from plants.extensions.logging import LogLevel
from plants.extensions.orm import Base, init_orm
from plants.modules.plant.event_dal import EventDAL
from plants.modules.plant.history_dal import HistoryDAL
from plants.modules.plant.models import Plant, Tag
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.plant.property_dal import PropertyDAL
from plants.modules.plant.schemas import FBPropagationType
from plants.modules.pollination.models import Florescence
from plants.modules.pollination.pollination_dal import PollinationDAL
from tests.config_test import generate_db_url
import plants as plants_package

TEST_DB_NAME = 'test_plants'


# redefine the event_loop fixture to have a session scope,
# see https://github.com/tortoise/tortoise-orm/issues/638
@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


async def _reset_db() -> None:
    """Create & Reset database to initial state."""
    # Create a engine/connection used for creating the test database
    engine_for_db_setup = create_async_engine(generate_db_url(),
                                              isolation_level='AUTOCOMMIT')

    # AsyncEngine.begin() provides a context manager that auto-commits at the end (or rolls back in
    # case of an error). Closes the connection at the end.
    async with engine_for_db_setup.begin() as setup_connection:
        setup_connection: AsyncConnection
        q = await setup_connection.execute(text(f"SELECT datname FROM pg_catalog.pg_database "
                                                f"where datname ='{TEST_DB_NAME}'"))
        if q.rowcount:
            await setup_connection.execute(text(f"DROP DATABASE {TEST_DB_NAME} WITH (FORCE);"))
        await setup_connection.execute(text(f"CREATE DATABASE {TEST_DB_NAME} ENCODING 'utf8'"))


@pytest_asyncio.fixture(scope="session")
async def connection() -> AsyncConnection:
    """Drop and Create a test database, yield a connection.
    Executed once per test session."""
    # Create a engine/connection used for creating the test database
    await _reset_db()

    # Create a new engine/connection that will actually connect
    # to the test database we just created. This will be the
    # connection used by the test suite run.
    engine: AsyncEngine = create_async_engine(generate_db_url(TEST_DB_NAME))
    async with engine.begin() as conn:
        yield conn

    # # setup_connection = engine_for_db_setup.connect()
    # with engine_for_db_setup.connect() as setup_connection:
    #     setup_connection.execute(text(f"DROP DATABASE {TEST_DB_NAME} WITH (FORCE);"))


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db(connection: AsyncConnection) -> None:
    """Setup test database.
    Creates all database tables as declared in SQLAlchemy models,
    then proceeds to drop all the created tables after all tests
    have finished running.
    Executed once per test session.
    """
    Base.metadata.bind = connection
    await init_orm(engine=connection.engine)


@pytest.fixture(scope="function")
def plant_dal(db: AsyncSession) -> PlantDAL:
    """
    """
    yield PlantDAL(db)


@pytest.fixture(scope="function")
def pollination_dal(db: AsyncSession) -> PollinationDAL:
    """
    """
    yield PollinationDAL(db)


@pytest.fixture(scope="function")
def history_dal(db: AsyncSession) -> HistoryDAL:
    """
    """
    yield HistoryDAL(db)


@pytest.fixture(scope="function")
def event_dal(db: AsyncSession) -> EventDAL:
    """
    """
    yield EventDAL(db)


@pytest.fixture(scope="function")
def property_dal(db: AsyncSession) -> PropertyDAL:
    """
    """
    yield PropertyDAL(db)


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncSession:
    """
    Create a new session for each test function.
    Truncate tables after each test.
    """
    db = await anext(get_db())
    yield db

    # we need to execute single statements with an async connection
    conn = await db.connection()
    await conn.execute(text("DELETE FROM history;"))
    await conn.execute(text("DELETE FROM tags;"))
    await conn.execute(text("DELETE FROM pollination;"))
    await conn.execute(text("DELETE FROM florescence;"))
    await conn.execute(text("DELETE FROM image;"))
    await conn.execute(text("DELETE FROM soil;"))
    await conn.execute(text("DELETE FROM pot;"))
    await conn.execute(text("DELETE FROM event;"))
    await conn.execute(text("DELETE FROM plants;"))
    # TRUNCATE table_a, table_b, …, table_z;
    await conn.commit()


@pytest_asyncio.fixture(scope="function")
async def plant_valid() -> Plant:
    plant = Plant(plant_name='Aloe Vera',
                  field_number="A100",
                  active=True,
                  deleted=False,
                  nursery_source="Some Nursery",
                  propagation_type=FBPropagationType.LEAF_CUTTING,
                  filename_previewimage="somefile.jpg",
                  tags=[Tag(text="new", state="Information"),
                        Tag(text="wow", state="Information")],
                  )
    return plant


@pytest_asyncio.fixture(scope="function")
async def plant_valid_in_db(db, plant_valid) -> Plant:
    db.add(plant_valid)
    await db.commit()
    return plant_valid


@pytest_asyncio.fixture(scope="function")
async def plant_valid_with_active_florescence() -> Plant:
    plant = Plant(plant_name='Gasteria obtusa',
                  active=True,
                  deleted=False,
                  tags=[Tag(text="thirsty", state="Information")],
                  florescences=[Florescence(
                      inflorescence_appearance_date=date(2023, 1, 1),  # '2023-01-01',
                      branches_count=1,
                      flowers_count=12,
                      florescence_status="flowering",
                      creation_context='manual'
                  )])
    return plant


@pytest_asyncio.fixture(scope="function")
async def plant_valid_with_active_florescence_in_db(db: AsyncSession, plant_valid_with_active_florescence) -> Plant:
    db.add(plant_valid_with_active_florescence)
    await db.commit()
    return plant_valid_with_active_florescence


@pytest_asyncio.fixture(scope="session")
def app() -> FastAPI:
    """
    only here do we import the main module. to avoid the regular database being initialized, we override
    the database url with a test database url
    we also override the get_db dependency called by most api endpoints to return a test database session
    """
    plants_package.local_config.connection_string = generate_db_url(TEST_DB_NAME)
    plants_package.local_config.log_settings.log_level_console = LogLevel.WARNING
    plants_package.local_config.log_settings.log_level_file = LogLevel.NONE
    from plants.main import app as main_app
    return main_app


@pytest_asyncio.fixture(scope="session")
async def ac(app) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://localhost") as ac:
        yield ac


@pytest.fixture(scope="function")
def valid_simple_plant_dict() -> dict:
    new_plant = {'plant_name': 'Aloe ferox',
                 'active': True,
                 'descendant_plants_all': [],
                 'sibling_plants': [],
                 'same_taxon_plants': [],
                 'tags': []}
    return new_plant


@pytest.fixture(scope="function")
def valid_another_simple_plant_dict() -> dict:
    new_plant = {'plant_name': 'Gasteria bicolor var. fallax',
                 'active': True,
                 'descendant_plants_all': [],
                 'sibling_plants': [],
                 'same_taxon_plants': [],
                 'tags': []}
    return new_plant


@pytest.fixture(scope="function")
def valid_florescence_dict() -> dict:
    valid_florescence = {
        'plant_id': 1,
        'florescence_status': 'flowering',
        'inflorescence_appearance_date': '2022-11-16',
        'comment': ' large & new',
    }
    return valid_florescence

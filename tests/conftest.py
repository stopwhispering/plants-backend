import pytest
from _pytest.fixtures import SubRequest
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session as OrmSession
from starlette.testclient import TestClient

from plants.dependencies import get_db
from plants.extensions.logging import LogLevel
from plants.extensions.orm import Base, init_orm
from plants.modules.plant.models import Plant, Tag
from plants.modules.plant.schemas import FBPropagationType
from plants.modules.pollination.models import Florescence
from tests.config_test import generate_db_url
import plants as plants_package

TEST_DB_NAME = 'test_plants'


@pytest.fixture(scope="session")
def connection() -> Connection:
    """Drop and Create a test database, yield a connection.
    Executed once per test session."""

    # Create a engine/connection used for creating the test database
    engine_for_db_setup = create_engine(generate_db_url(),
                                        isolation_level='AUTOCOMMIT')
    with engine_for_db_setup.connect() as setup_connection:
        if (setup_connection.execute(text(f"SELECT datname FROM pg_catalog.pg_database "
                                          f"where datname ='{TEST_DB_NAME}'")).rowcount):
            setup_connection.execute(text(f"DROP DATABASE {TEST_DB_NAME} WITH (FORCE);"))
        setup_connection.execute(text(f"CREATE DATABASE {TEST_DB_NAME} ENCODING 'utf8'"))

    # Create a new engine/connection that will actually connect
    # to the test database we just created. This will be the
    # connection used by the test suite run.
    engine = create_engine(generate_db_url(TEST_DB_NAME))
    connection = engine.connect()
    yield connection
    connection.close()

    # # setup_connection = engine_for_db_setup.connect()
    # with engine_for_db_setup.connect() as setup_connection:
    #     setup_connection.execute(text(f"DROP DATABASE {TEST_DB_NAME} WITH (FORCE);"))


@pytest.fixture(scope="session", autouse=True)
def setup_db(connection: Connection, request: SubRequest) -> None:
    """Setup test database.
    Creates all database tables as declared in SQLAlchemy models,
    then proceeds to drop all the created tables after all tests
    have finished running.
    Executed once per test session.
    """
    Base.metadata.bind = connection

    init_orm(engine=connection.engine)

    def teardown() -> None:
        pass
        # Base.metadata.drop_all(bind=connection)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def db(connection: Connection) -> OrmSession:
    """
    Create a new session for each test function.
    Truncate tables after each test.
    """
    # session = SessionFactory.create_session()
    # yield session
    # session.close()
    yield next(get_db())

    # connection.execute(text(f"TRUNCATE plants CASCADE;"))  # freezes sometimes
    sql = """
    DELETE FROM history; 
    DELETE FROM tags; 
    DELETE FROM pollination; 
    DELETE FROM florescence; 
    DELETE FROM plants;
    """
    connection.execute(text(sql))
    # TRUNCATE table_a, table_b, …, table_z;
    connection.commit()


@pytest.fixture(scope="function")
def plant_valid() -> Plant:
    plant = Plant(plant_name='Aloe Vera',
                  field_number="A100",
                  active=True,
                  nursery_source="Some Nursery",
                  propagation_type=FBPropagationType.LEAF_CUTTING,
                  filename_previewimage="somefile.jpg",
                  tags=[Tag(text="new", state="Information"),
                        Tag(text="wow", state="Information")],
                  )
    return plant


@pytest.fixture(scope="function")
def plant_valid_in_db(db, plant_valid) -> Plant:
    db.add(plant_valid)
    db.commit()
    return plant_valid


@pytest.fixture(scope="function")
def plant_valid_with_active_florescence() -> Plant:
    plant = Plant(plant_name='Gasteria obtusa',
                  active=True,
                  tags=[Tag(text="thirsty", state="Information")],
                  florescences=[Florescence(
                      inflorescence_appearance_date='2023-01-01',
                      branches_count=1,
                      flowers_count=12,
                      florescence_status="flowering",
                      creation_context='manual'
                  )])
    return plant


@pytest.fixture(scope="function")
def plant_valid_with_active_florescence_in_db(db, plant_valid_with_active_florescence) -> Plant:
    db.add(plant_valid_with_active_florescence)
    db.commit()
    return plant_valid_with_active_florescence


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def test_client(app) -> TestClient:
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def valid_simple_plant_dict(app) -> dict:
    new_plant = {'plant_name': 'Aloe ferox',
                 'active': True,
                 'descendant_plants_all': [],
                 'sibling_plants': [],
                 'same_taxon_plants': [],
                 'tags': []}
    return new_plant


@pytest.fixture(scope="function")
def valid_another_simple_plant_dict(app) -> dict:
    new_plant = {'plant_name': 'Gasteria bicolor var. fallax',
                 'active': True,
                 'descendant_plants_all': [],
                 'sibling_plants': [],
                 'same_taxon_plants': [],
                 'tags': []}
    return new_plant


@pytest.fixture(scope="function")
def valid_florescence_dict(app) -> dict:
    valid_florescence = {
        'plant_id': 1,
        'florescence_status': 'flowering',
        'inflorescence_appearance_date': '2022-11-16',
        'comment': ' large & new',
    }
    return valid_florescence

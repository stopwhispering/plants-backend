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
from plants.modules.plant.models import Plant
from plants.tests.config_test import generate_db_url
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
    with engine_for_db_setup.connect() as setup_connection:
        setup_connection.execute(text(f"DROP DATABASE {TEST_DB_NAME} WITH (FORCE);"))


@pytest.fixture(scope="session", autouse=True)
def setup_db(connection: Connection, request: SubRequest) -> None:
    """Setup test database.
    Creates all database tables as declared in SQLAlchemy models,
    then proceeds to drop all the created tables after all tests
    have finished running.
    Executed once per test session.
    """
    Base.metadata.bind = connection
    # Base.metadata.create_all()

    init_orm(engine=connection.engine)
    request.addfinalizer(lambda: Base.metadata.drop_all(bind=connection))


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
    connection.execute(text(f"DELETE FROM plants;"))
    # TRUNCATE table_a, table_b, …, table_z;
    connection.commit()


@pytest.fixture(scope="session")
def plant_valid() -> Plant:
    plant = Plant(plant_name='Aloe Vera',)
    return plant


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

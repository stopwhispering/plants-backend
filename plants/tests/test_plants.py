from unittest import TestCase

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from plants.extensions.db import init_database_tables, Base
from plants.dependencies import get_db
from plants.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
        )
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
init_database_tables(engine_=engine, session=TestingSessionLocal())


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class Test(TestCase):

    @classmethod
    def tearDownClass(cls) -> None:
        """drop whole test database; using memory sqlite instead doesn't work as somehow it is
        reset inbetween initial population with tables and execution of test methods"""
        Base.metadata.create_all(bind=engine)

    def test_create_plant(self):
        """create empty plant"""
        new_plant = {
            'plant_name': 'New Plant',
            'active':     'True',
            }

        response = client.post(
                "/plants_tagger/backend/plants/",
                json={
                    'PlantsCollection': [new_plant]
                    }
                )
        assert response.status_code == 200, response.text
        assert response.json()['action'] == 'Saved Plants', response.json()['action']
        assert isinstance(response.json()['plants'][0]['id'], int), response.json()['plants'][0]['id']

    def test_get_plants(self):
        response = client.get(
                "/plants_tagger/backend/plants/"
                )
        print(response.json())
        print(response.status_code)


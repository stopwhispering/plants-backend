from __future__ import annotations

import asyncio
import json
import shutil
import sys
from asyncio import AbstractEventLoop
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio
import pytz
from dateutil.relativedelta import relativedelta
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

import plants as plants_package
from plants.constants import (
    FILENAME_GERMINATION_DAYS_ESTIMATOR,
    FILENAME_GERMINATION_PROBABILITY_ESTIMATOR,
    FILENAME_PICKLED_POLLINATION_ESTIMATOR,
    FILENAME_RIPENING_DAYS_ESTIMATOR,
)
from plants.extensions import orm
from plants.extensions.logging import LogLevel
from plants.extensions.orm import Base, init_orm
from plants.modules.event.enums import FBShapeSide, FBShapeTop, PotMaterial
from plants.modules.event.event_dal import EventDAL
from plants.modules.event.models import Event, Observation, Pot, Soil
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.enums import FBPropagationType, TagState
from plants.modules.plant.models import Plant, Tag
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.enums import (
    Context,
    FlorescenceStatus,
    Location,
    PollenQuality,
    PollenType,
    PollinationStatus,
    SeedPlantingStatus,
)
from plants.modules.pollination.florescence_dal import FlorescenceDAL
from plants.modules.pollination.models import Florescence, Pollination, SeedPlanting
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.pollination.seed_planting_dal import SeedPlantingDAL
from plants.modules.taxon.models import Taxon
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.api_utils import date_hook
from plants.shared.history_dal import HistoryDAL
from plants.shared.orm_util import clone_orm_instance
from tests.config_test import create_tables_if_required, generate_db_url

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI

TEST_DB_NAME = "test_plants"

# required to make psycopg3 async work on windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# redefine the event_loop fixture to have a session scope,
# see https://github.com/tortoise/tortoise-orm/issues/638
@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    # return asyncio.get_event_loop()
    return asyncio.new_event_loop()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db() -> None:
    """Setup test database: Create & Reset database to initial state; Create all database tables as
    declared in SQLAlchemy models;"""
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
    setup_connection: AsyncConnection
    async with engine_for_db_setup.begin() as setup_connection:
        await setup_connection.execute(text("DROP SCHEMA public CASCADE;"))
        await setup_connection.execute(text("CREATE SCHEMA public;"))

        Base.metadata.bind = setup_connection  # type: ignore[attr-defined]
        await init_orm(engine=setup_connection.engine)
        await create_tables_if_required(engine=setup_connection.engine)


def _reset_paths() -> None:
    """Warning: Make sure the pats are set to test paths before calling this
    function!"""
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
async def test_db() -> AsyncGenerator[AsyncSession, None]:
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
        await conn.execute(text("DELETE FROM seed_planting;"))
        await conn.execute(text("DELETE FROM pollination;"))
        await conn.execute(text("DELETE FROM florescence;"))
        await conn.execute(text("DELETE FROM image_keywords;"))
        await conn.execute(text("DELETE FROM image_to_plant_association;"))
        await conn.execute(text("DELETE FROM image;"))
        await conn.execute(text("DELETE FROM pot;"))
        await conn.execute(text("DELETE FROM observation;"))
        await conn.execute(text("DELETE FROM event;"))
        await conn.execute(text("DELETE FROM soil;"))
        await conn.execute(text("DELETE FROM plants;"))
        await conn.execute(text("DELETE FROM distribution;"))
        await conn.execute(text("DELETE FROM taxon_to_occurrence_association;"))
        await conn.execute(text("DELETE FROM taxon;"))
        # TRUNCATE table_a, table_b, …, table_z;
        await conn.commit()
        await conn.close()

        _reset_paths()


@pytest_asyncio.fixture(scope="function")
async def plant_valid() -> Plant:
    return Plant(
        plant_name="Aloe Vera",
        field_number="A100",
        active=True,
        deleted=False,
        nursery_source="Worldwide Cactus",
        propagation_type=FBPropagationType.LEAF_CUTTING,
        tags=[
            Tag(text="new", state=TagState.INFORMATION),
            Tag(text="wow", state=TagState.INFORMATION),
        ],
        count_stored_pollen_containers=3,
    )


@pytest_asyncio.fixture(scope="function")
async def plant_valid_in_db(
    plant_valid: Plant, taxa_in_db: list[Taxon], plant_dal: PlantDAL
) -> Plant:
    """create a valid plant in the database and return it."""
    plant_valid.taxon = taxa_in_db[0]
    # test_db.add(plant_valid)
    #  # re-read to have joined relations ready
    # await test_db.commit()
    await plant_dal.save_plant(plant_valid)
    # plant_valid = await plant_dal.by_id(plant_valid.id, eager_load=True)
    return plant_valid


@pytest_asyncio.fixture(scope="function")
async def valid_plant_in_db_with_image(
    ac: AsyncClient,
    plant_valid_in_db: Plant,
    plant_dal: PlantDAL,
) -> Plant:
    """upload an image for the plant and return it."""
    plant_id = plant_valid_in_db.id
    path = Path(__file__).resolve().parent.joinpath("./static/demo_valid_plant.jpg")
    files = [
        (
            "files[]",
            ("demo_image_plant.jpg", path.open("rb")),
        )
    ]
    response = await ac.post(f"/api/plants/{plant_id}/images/", files=files)
    assert response.status_code == 200
    resp = response.json()

    # also set some keywords and set a description
    modified_image = resp["images"][0].copy()
    modified_image["keywords"] = [{"keyword": "flower"}, {"keyword": "new leaf"}]
    modified_image["description"] = " some description  "  # will be stripped
    payload = {"ImagesCollection": [modified_image]}  # BImageUpdated
    await ac.put("/api/images/", json=payload)

    # reload to have image reations available
    plant_dal.expire(plant_valid_in_db)
    await plant_dal.by_id(plant_id, eager_load=True)
    assert plant_valid_in_db.images
    return plant_valid_in_db


@pytest_asyncio.fixture(scope="function")
async def plant_in_db_with_image_and_events(
    test_db: AsyncSession,
    valid_plant_in_db_with_image: Plant,
    soil_in_db: Soil,
) -> Plant:
    """Create events for plant."""
    event = Event(
        date="2021-01-01",
        event_notes="Event Note 1",
        soil=soil_in_db,
        plant=valid_plant_in_db_with_image,
        images=[valid_plant_in_db_with_image.images[0]],
    )
    pot = Pot(
        event=event,
        material=PotMaterial.TERRACOTTA,
        shape_top=FBShapeTop.HEXAGONAL,
        shape_side=FBShapeSide.FLAT,
        diameter_width=Decimal(10.4),
    )
    observation = Observation(
        event=event,
        diseases="some disease",
    )

    test_db.add(event)
    test_db.add(observation)
    test_db.add(pot)
    await test_db.flush()
    return valid_plant_in_db_with_image


@pytest_asyncio.fixture(scope="function")
async def plant_valid_with_active_florescence() -> Plant:
    return Plant(
        plant_name="Gasteria obtusa",
        active=True,
        deleted=False,
        tags=[Tag(text="thirsty", state=TagState.INFORMATION)],
        florescences=[
            Florescence(
                inflorescence_appeared_at=date(2023, 1, 1),  # '2023-01-01',
                branches_count=1,
                flowers_count=12,
                florescence_status=FlorescenceStatus.FLOWERING,
                creation_context=Context.MANUAL,
            )
        ],
    )


@pytest_asyncio.fixture(scope="function")
async def plant_valid_with_active_florescence_in_db(
    test_db: AsyncSession, plant_valid_with_active_florescence: Plant
) -> Plant:
    test_db.add(plant_valid_with_active_florescence)
    await test_db.commit()
    return plant_valid_with_active_florescence


@pytest_asyncio.fixture(scope="function", autouse=True)
def reset_paths() -> None:
    """reset paths before each test function."""
    _reset_paths()


@pytest_asyncio.fixture(scope="session", autouse=True)
def set_test_paths() -> None:
    """To avoid the regular database being initialized, we override the database url with a test
    database url we also override the get_db dependency called by most api endpoints to return a
    test database session."""
    plants_package.local_config.connection_string = str(generate_db_url(TEST_DB_NAME))
    plants_package.local_config.max_images_per_taxon = 2

    plants_package.local_config.log_settings.log_level_console = LogLevel.WARNING
    plants_package.local_config.log_settings.log_level_file = LogLevel.NONE

    plants_package.settings.paths.path_photos = Path("/common/plants_test/photos")
    plants_package.settings.paths.path_deleted_photos = Path("/common/plants_test/photos/deleted")
    plants_package.settings.paths.path_pickled_ml_models = Path("/common/plants_test/pickled")


@pytest_asyncio.fixture(scope="session")
def app() -> FastAPI:
    """only here do we import the main module."""
    from plants.main import app as main_app

    return main_app


@pytest_asyncio.fixture(scope="session")
async def ac(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://localhost") as ac:
        yield ac


@pytest.fixture()
def valid_simple_plant_dict() -> dict[str, Any]:
    return {
        "plant_name": "Aloe ferox",
        "active": True,
        # 'descendant_plants_all': [],
        # 'sibling_plants': [],
        # 'same_taxon_plants': [],
        "tags": [],
        # "taxon_tags": [],
    }


@pytest_asyncio.fixture(scope="function")
async def another_valid_plant_in_db(test_db: AsyncSession, taxa_in_db: list[Taxon]) -> Plant:
    """create a valid plant in the database and return it."""
    new_plant_data = {
        "plant_name": "Gasteria bicolor var. fallax",
        "active": True,
        "deleted": False,
        "tags": [],
        "taxon_id": taxa_in_db[1].id,
    }
    new_plant = Plant(**new_plant_data)  # type:ignore[arg-type]
    test_db.add(new_plant)
    await test_db.commit()
    return new_plant


@pytest.fixture()
def valid_florescence_dict() -> dict[str, Any]:
    return {
        "plant_id": 1,
        "florescence_status": "flowering",
        "inflorescence_appeared_at": "2022-11-16",
        "comment": " large & new",
    }


@pytest.fixture()
def plant_dal(test_db: AsyncSession) -> PlantDAL:
    """"""
    return PlantDAL(test_db)


@pytest.fixture()
def pollination_dal(test_db: AsyncSession) -> PollinationDAL:
    """"""
    return PollinationDAL(test_db)


@pytest.fixture()
def seed_planting_dal(test_db: AsyncSession) -> SeedPlantingDAL:
    """"""
    return SeedPlantingDAL(test_db)


@pytest.fixture()
def florescence_dal(test_db: AsyncSession) -> FlorescenceDAL:
    """"""
    return FlorescenceDAL(test_db)


@pytest.fixture()
def taxon_dal(test_db: AsyncSession) -> TaxonDAL:
    """"""
    return TaxonDAL(test_db)


@pytest.fixture()
def history_dal(test_db: AsyncSession) -> HistoryDAL:
    """"""
    return HistoryDAL(test_db)


@pytest.fixture()
def event_dal(test_db: AsyncSession) -> EventDAL:
    """"""
    return EventDAL(test_db)


@pytest.fixture()
def image_dal(test_db: AsyncSession) -> ImageDAL:
    """"""
    return ImageDAL(test_db)


@pytest_asyncio.fixture(scope="function")
# async def taxon_in_db(test_db: AsyncSession) -> Taxon:
async def taxa_in_db(test_db: AsyncSession) -> list[Taxon]:
    """Create a valid taxon in the db and return it."""
    path = Path(__file__).resolve().parent.joinpath("./data/demo_taxa.json")
    with path.open() as f:
        taxon_dicts = json.load(f)

    taxa = [Taxon(**taxon_dict) for taxon_dict in taxon_dicts]
    test_db.add_all(taxa)

    # taxon_dict = taxa[0]
    # taxon = Taxon(**taxon_dict)
    #
    # test_db.add(taxon)
    await test_db.commit()

    return taxa


@pytest_asyncio.fixture(scope="function")
async def trained_pollination_ml_model() -> None:
    path_pickled_demo_pipeline = (
        Path(__file__)
        .resolve()
        .parent.joinpath("./static/")
        .joinpath(FILENAME_PICKLED_POLLINATION_ESTIMATOR)
    )
    target_path = plants_package.settings.paths.path_pickled_ml_models.joinpath(
        FILENAME_PICKLED_POLLINATION_ESTIMATOR
    )

    target_path.write_bytes(path_pickled_demo_pipeline.read_bytes())


@pytest_asyncio.fixture(scope="function")
async def trained_models() -> None:
    path_demo = (
        Path(__file__)
        .resolve()
        .parent.joinpath("./static/")
        .joinpath(FILENAME_PICKLED_POLLINATION_ESTIMATOR)
    )
    target_path = plants_package.settings.paths.path_pickled_ml_models.joinpath(
        FILENAME_PICKLED_POLLINATION_ESTIMATOR
    )
    target_path.write_bytes(path_demo.read_bytes())

    path_pickled_demo_pipeline = (
        Path(__file__)
        .resolve()
        .parent.joinpath("./static/")
        .joinpath(FILENAME_RIPENING_DAYS_ESTIMATOR)
    )
    target_path = plants_package.settings.paths.path_pickled_ml_models.joinpath(
        FILENAME_RIPENING_DAYS_ESTIMATOR
    )
    target_path.write_bytes(path_pickled_demo_pipeline.read_bytes())

    path_pickled_demo_pipeline = (
        Path(__file__)
        .resolve()
        .parent.joinpath("./static/")
        .joinpath(FILENAME_GERMINATION_PROBABILITY_ESTIMATOR)
    )
    target_path = plants_package.settings.paths.path_pickled_ml_models.joinpath(
        FILENAME_GERMINATION_PROBABILITY_ESTIMATOR
    )
    target_path.write_bytes(path_pickled_demo_pipeline.read_bytes())

    path_pickled_demo_pipeline = (
        Path(__file__)
        .resolve()
        .parent.joinpath("./static/")
        .joinpath(FILENAME_GERMINATION_DAYS_ESTIMATOR)
    )
    target_path = plants_package.settings.paths.path_pickled_ml_models.joinpath(
        FILENAME_GERMINATION_DAYS_ESTIMATOR
    )
    target_path.write_bytes(path_pickled_demo_pipeline.read_bytes())


@pytest_asyncio.fixture(scope="function")
async def finished_pollinations_in_db(
    plant_valid_in_db: Plant,
    another_valid_plant_in_db: Plant,
    test_db: AsyncSession,
) -> list[Pollination]:
    """To train the pollination ml model, we need at least three finished pollination attempts."""
    pollination_1 = Pollination(
        seed_capsule_plant_id=plant_valid_in_db.id,
        pollen_donor_plant_id=another_valid_plant_in_db.id,
        pollen_type=PollenType.FROZEN,
        pollen_quality=PollenQuality.GOOD,
        location=Location.INDOOR,
        creation_at_context=Context.API,
        pollination_status=PollinationStatus.GERMINATED,
        ongoing=False,
    )
    pollination_2 = Pollination(
        seed_capsule_plant_id=plant_valid_in_db.id,
        pollen_donor_plant_id=another_valid_plant_in_db.id,
        pollen_type=PollenType.FRESH,
        pollen_quality=PollenQuality.BAD,
        location=Location.INDOOR,
        creation_at_context=Context.API,
        pollination_status=PollinationStatus.SEED,
        ongoing=False,
    )
    pollination_3 = Pollination(
        seed_capsule_plant_id=another_valid_plant_in_db.id,
        pollen_donor_plant_id=plant_valid_in_db.id,
        pollen_type=PollenType.FRESH,
        pollen_quality=PollenQuality.GOOD,
        location=Location.INDOOR,
        creation_at_context=Context.API,
        pollination_status=PollinationStatus.ATTEMPT,
        ongoing=False,
    )
    clones_1 = [clone_orm_instance(pollination_1) for _ in range(20)]
    clones_2 = [clone_orm_instance(pollination_2) for _ in range(20)]
    clones_3 = [clone_orm_instance(pollination_3) for _ in range(20)]
    pollinations = [
        pollination_1,
        pollination_2,
        pollination_3,
        *clones_1,
        *clones_2,
        *clones_3,
    ]
    test_db.add_all(pollinations)
    await test_db.commit()
    return pollinations


@pytest_asyncio.fixture(scope="function")
async def florescence_dict() -> dict[str, Any]:
    """Read florescence dict from json; has no plant attached."""
    path_florescence = Path(__file__).resolve().parent.joinpath("./data/demo_florescence.json")
    with path_florescence.open() as file:
        return json.load(file, object_hook=date_hook)  # type:ignore[no-any-return]


@pytest_asyncio.fixture(scope="function")
async def pollination_dict() -> dict[str, Any]:
    """Read pollination dict from json; has no florescence, seed_capsule_plant, or
    pollen_donor_plant attached."""
    path_pollination = Path(__file__).resolve().parent.joinpath("./data/demo_pollination.json")
    with path_pollination.open() as file:
        return json.load(file, object_hook=date_hook)  # type:ignore[no-any-return]


@pytest_asyncio.fixture(scope="function")
async def pollination_in_db(
    test_db: AsyncSession,
    florescence_dict: dict[str, Any],
    pollination_dict: dict[str, Any],
    plant_valid_in_db: Plant,
    another_valid_plant_in_db: Plant,
) -> Pollination:
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

    return pollination


@pytest_asyncio.fixture(scope="function")
async def seed_plantings_in_db(
    test_db: AsyncSession,
    pollination_in_db: Pollination,
    pollination_dal: PollinationDAL,
    soil_in_db: Soil,
) -> list[SeedPlanting]:
    """Create seed plantings in the db and return them."""
    # have seed plantings loaded
    pollination_in_db = await pollination_dal.by_id(pollination_in_db.id)
    one_year_ago = (datetime.now(tz=pytz.utc) - relativedelta(years=1)).date()
    one_week_ago = (datetime.now(tz=pytz.utc) - relativedelta(days=7)).date()
    pollination_in_db.seed_plantings = [
        SeedPlanting(
            status=SeedPlantingStatus.PLANTED,
            comment="Active with known linked Pollination",
            sterilized=True,
            soaked=True,
            covered=True,
            planted_on=one_week_ago,
            count_planted=10,
            soil=soil_in_db,
        ),
        SeedPlanting(
            status=SeedPlantingStatus.ABANDONED,
            comment="Abandoned with known linked Pollination",
            sterilized=True,
            soaked=True,
            covered=True,
            planted_on=one_week_ago,
            count_planted=10,
            soil=soil_in_db,
        ),
        SeedPlanting(
            status=SeedPlantingStatus.GERMINATED,
            comment="Germinated not long ago",
            sterilized=True,
            soaked=True,
            covered=True,
            planted_on=one_year_ago,
            germinated_first_on=one_week_ago,
            count_planted=10,
            soil=soil_in_db,
        ),
        SeedPlanting(
            status=SeedPlantingStatus.GERMINATED,
            comment="Germinated long ago",
            sterilized=True,
            soaked=True,
            covered=True,
            planted_on=one_year_ago,
            germinated_first_on=one_year_ago,
            count_planted=10,
            soil=soil_in_db,
        ),
    ]

    await test_db.commit()

    return pollination_in_db.seed_plantings


@pytest_asyncio.fixture(scope="function")
async def soil_in_db(test_db: AsyncSession) -> Soil:
    """Create a valid soil in the db and return it."""
    soil = Soil(
        soil_name="Pumice",
        mix="100% Pumice",
        description="Pure Pumice, 3-5mm",
    )
    test_db.add(soil)
    await test_db.commit()

    return soil

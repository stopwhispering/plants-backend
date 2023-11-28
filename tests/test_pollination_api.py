from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import pytest

from plants.modules.pollination.enums import (
    COLORS_MAP_TO_RGB,
    Context,
    FlorescenceStatus,
    Location,
    PollenQuality,
    PollenType,
)
from plants.modules.pollination.models import Florescence
from plants.modules.pollination.schemas import (
    CreateUpdatePollenContainersRequest,
    PollenContainerCreateUpdate,
    PollinationCreate,
)
from plants.shared.api_constants import FORMAT_API_YYYY_MM_DD_HH_MM
from plants.shared.typing_util import cast_not_none

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.pollination.florescence_dal import FlorescenceDAL
    from plants.modules.pollination.models import Pollination
    from plants.modules.pollination.pollination_dal import PollinationDAL


@pytest.mark.usefixtures("trained_models")
@pytest.mark.asyncio()
async def test_create_pollination(
    ac: AsyncClient,
    plant_valid_with_active_florescence_in_db: Plant,
    valid_simple_plant_dict: dict[str, Any],
    plant_dal: PlantDAL,
    pollination_dal: PollinationDAL,
) -> None:
    """Includes creation of pollen container."""
    # via test client:
    # create plant 2 with pollen container for it
    # payload = {"PlantsCollection": [valid_simple_plant_dict]}
    response = await ac.post("/api/plants/", json=valid_simple_plant_dict)
    assert response.status_code == 200
    assert (p := response.json().get("plant")) is not None
    payload_pc = CreateUpdatePollenContainersRequest(
        pollen_container_collection=[
            PollenContainerCreateUpdate(
                plant_id=p["id"],
                # plant_name=p["plant_name"],
                # genus="Aloe",
                count_stored_pollen_containers=4,
            )
        ]
    )
    response = await ac.post("/api/pollen_containers", json=payload_pc.model_dump())
    assert response.status_code == 200

    plant2: Plant | None = await plant_dal.by_name(p["plant_name"])
    assert plant2 is not None
    assert plant2.count_stored_pollen_containers == 4

    # create a florescence from active florescence and container
    # PollinationCreate
    payload_pollination = PollinationCreate(
        florescence_id=plant_valid_with_active_florescence_in_db.florescences[0].id,
        seed_capsule_plant_id=plant_valid_with_active_florescence_in_db.id,
        pollen_donor_plant_id=plant2.id,
        pollen_type=PollenType.FROZEN,
        pollen_quality=PollenQuality.GOOD,
        pollinated_at="2022-11-16 12:06",
        label_color_rgb="#ff7c09",
        location=Location.INDOOR,
        count_attempted=3,
    )
    response = await ac.post("/api/pollinations", json=payload_pollination.model_dump())
    assert response.status_code == 200
    pollinations = await pollination_dal.get_pollinations_by_plant_ids(
        plant_valid_with_active_florescence_in_db.id, plant2.id
    )
    assert len(pollinations) == 1
    pollination = pollinations[0]
    assert pollination.pollen_type == "frozen"
    assert pollination.location == "indoor"
    assert pollination.count_attempted == 3


@pytest.mark.usefixtures("trained_models")
@pytest.mark.asyncio()
async def test_get_pollinations(
    ac: AsyncClient,
    # pollination_dal: PollinationDAL,
    pollination_in_db: Pollination,
) -> None:
    """Update a pollination."""
    # get pollination via test client
    response = await ac.get("/api/ongoing_pollinations")
    assert response.status_code == 200
    resp = response.json()

    ongoing_pollinations = resp["ongoing_pollination_collection"]
    pollination = next(p for p in ongoing_pollinations if p["id"] == pollination_in_db.id)
    assert pollination["seed_capsule_plant_id"] == (pollination_in_db.seed_capsule_plant_id)
    assert pollination["pollen_donor_plant_id"] == (pollination_in_db.pollen_donor_plant_id)
    assert pollination["pollen_type"] == pollination_in_db.pollen_type
    assert pollination["location"] == pollination_in_db.location

    pollination_in_db.pollinated_at = cast_not_none(pollination_in_db.pollinated_at)
    assert pollination["pollinated_at"] == (
        pollination_in_db.pollinated_at.strftime(FORMAT_API_YYYY_MM_DD_HH_MM)
    )

    pollination_in_db.label_color = cast_not_none(pollination_in_db.label_color)
    assert pollination["label_color_rgb"] == COLORS_MAP_TO_RGB[pollination_in_db.label_color]


@pytest.mark.usefixtures("trained_models")
@pytest.mark.asyncio()
async def test_update_pollination(
    ac: AsyncClient,
    test_db: AsyncSession,
    pollination_in_db: Pollination,
) -> None:
    """Update a pollination."""
    # get pollination via test client
    response = await ac.get("/api/ongoing_pollinations")
    assert response.status_code == 200
    resp = response.json()
    pollination = next(
        p for p in resp["ongoing_pollination_collection"] if p["id"] == pollination_in_db.id
    )

    # update attributes and send via test client
    pollination["location"] = "indoor"
    pollination["count_attempted"] = 2
    pollination["seed_capsule_length"] = 14.5
    pollination["label_color_rgb"] = "#ffffff"
    response = await ac.put(f"/api/pollinations/{pollination['id']}", json=pollination)
    assert response.status_code == 200

    # check if attributes have been updated
    await test_db.refresh(pollination_in_db)
    assert pollination_in_db.location == "indoor"
    assert pollination_in_db.count_attempted == 2
    assert pollination_in_db.seed_capsule_length == 14.5
    assert pollination_in_db.label_color == "white"


@pytest.mark.usefixtures("finished_pollinations_in_db")
@pytest.mark.asyncio()
async def test_train_pollination_ml_model(
    # ac: AsyncClient,
) -> None:
    pass

    # for assembling training data, we currently need a sync connection for pandas
    # with PsycoPG3 async driver, this results in some bad password error
    # --> try again after changing data collection for ml training

    # response = await ac.post("/api/retrain_probability_pollination_to_seed_model")
    # assert response.status_code == 200
    # resp = response.json()
    #
    # assert "metric_name" in resp
    # assert "model" in resp
    # assert "metric_value" in resp
    # assert isinstance(resp["metric_value"], float)
    # assert 0.0 < resp["metric_value"] <= 1.0
    #
    # # test pickled model exists
    # file_paths = list(plants_package.settings.paths.path_pickled_ml_models.glob("*"))
    # file_names = [f.name for f in file_paths]
    # assert FILENAME_PICKLED_POLLINATION_ESTIMATOR in file_names


@pytest.mark.usefixtures("trained_pollination_ml_model", "plant_valid_in_db")
@pytest.mark.asyncio()
async def test_get_pollen_donors(
    ac: AsyncClient,
    plant_valid_with_active_florescence_in_db: Plant,
    another_valid_plant_in_db: Plant,  # will be created other florescences for
    florescence_dal: FlorescenceDAL,
    plant_valid_in_db: Plant,  # has frozen pollen container
) -> None:
    """Get potential pollination pollen donor plants (from active florescences and pollen
    containers).

    plant_valid_in_db ('aloe vera') has frozen pollen container; additionally, we insert two other
    active florescences ('gasteria bicolor var. fallax') and expect only one of them to be returned.
    """
    florescence_id = plant_valid_with_active_florescence_in_db.florescences[0].id
    another_plant_with_active_florescences_id = another_valid_plant_in_db.id

    await florescence_dal.create_florescence(
        Florescence(
            # plant=another_valid_plant_in_db,
            plant_id=another_plant_with_active_florescences_id,
            inflorescence_appeared_at=date(2023, 5, 1),  # '2023-01-01',
            branches_count=1,
            flowers_count=12,
            florescence_status=FlorescenceStatus.FLOWERING,
            creation_context=Context.MANUAL,
        )
    )
    await florescence_dal.create_florescence(
        Florescence(
            # plant=another_valid_plant_in_db,
            plant_id=another_plant_with_active_florescences_id,
            inflorescence_appeared_at=date(2023, 4, 21),
            branches_count=2,
            flowers_count=14,
            florescence_status=FlorescenceStatus.FLOWERING,
            creation_context=Context.MANUAL,
        )
    )

    response = await ac.get(f"/api/potential_pollen_donors/{florescence_id}")
    assert response.status_code == 200
    resp = response.json()

    potential_pollen_donors = resp["potential_pollen_donor_collection"]
    assert len(potential_pollen_donors) == 2

    frozen = next(p for p in potential_pollen_donors if p["plant_id"] == plant_valid_in_db.id)
    assert frozen["pollen_type"] == "frozen"

    active = next(
        p
        for p in potential_pollen_donors
        if p["plant_id"] == another_plant_with_active_florescences_id
    )
    assert active["pollen_type"] == "fresh"

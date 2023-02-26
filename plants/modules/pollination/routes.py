import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from plants.dependencies import (
    get_florescence_dal,
    get_plant_dal,
    get_pollination_dal,
    valid_florescence,
    valid_pollination,
)
from plants.modules.pollination.enums import COLORS_MAP
from plants.modules.pollination.florescence_services import (
    create_new_florescence,
    read_active_florescences,
    read_plants_for_new_florescence,
    remove_florescence,
    update_active_florescence,
)
from plants.modules.pollination.flower_history_services import generate_flower_history
from plants.modules.pollination.ml_model import (
    train_model_for_probability_of_seed_production,
)
from plants.modules.pollination.pollination_services import (
    read_ongoing_pollinations,
    read_plants_without_pollen_containers,
    read_pollen_containers,
    read_potential_pollen_donors,
    remove_pollination,
    save_new_pollination,
    update_pollen_containers,
    update_pollination,
)
from plants.modules.pollination.schemas import (
    BResultsActiveFlorescences,
    BResultsFlowerHistory,
    BResultsOngoingPollinations,
    BResultsPlantsForNewFlorescence,
    BResultsPollenContainers,
    BResultsPotentialPollenDonors,
    BResultsRetrainingPollinationToSeedsModel,
    FlorescenceCreate,
    FlorescenceUpdate,
    FRequestPollenContainers,
    PollinationCreate,
    PollinationUpdate,
    SettingsRead,
)
from plants.shared.message_services import get_message

if TYPE_CHECKING:
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.pollination.florescence_dal import FlorescenceDAL
    from plants.modules.pollination.models import Florescence, Pollination
    from plants.modules.pollination.pollination_dal import PollinationDAL

logger = logging.getLogger(__name__)

router = APIRouter(
    # prefix="/pollination",
    tags=["pollination", "inflorence"],
    responses={404: {"description": "Not found"}},
)


@router.post("/pollinations")
async def post_pollination(
    new_pollination_data: PollinationCreate,
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
):
    await save_new_pollination(
        new_pollination_data=new_pollination_data,
        pollination_dal=pollination_dal,
        florescence_dal=florescence_dal,
        plant_dal=plant_dal,
    )


@router.put("/pollinations/{pollination_id}")
async def put_pollination(
    edited_pollination_data: PollinationUpdate,
    pollination: Pollination = Depends(valid_pollination),
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
):
    if pollination.id != edited_pollination_data.id:
        raise HTTPException(
            status_code=400,
            detail=f"Pollination ID in path ({pollination.id}) does not match "
            f"pollination ID in body ({edited_pollination_data.id}).",
        )
    await update_pollination(
        pollination,
        pollination_data=edited_pollination_data,
        pollination_dal=pollination_dal,
    )


@router.get("/ongoing_pollinations", response_model=BResultsOngoingPollinations)
async def get_ongoing_pollinations(pollination_dal=Depends(get_pollination_dal)):
    ongoing_pollinations = await read_ongoing_pollinations(
        pollination_dal=pollination_dal
    )
    return {
        "action": "Get ongoing pollinations",
        "message": get_message(
            f"Provided {len(ongoing_pollinations)} ongoing pollinations."
        ),
        "ongoingPollinationCollection": ongoing_pollinations,
    }


@router.get("/pollinations/settings", response_model=SettingsRead)
async def get_pollination_settings():
    colors = list(COLORS_MAP.keys())
    return {
        "colors": colors,
    }


@router.get("/pollen_containers", response_model=BResultsPollenContainers)
async def get_pollen_containers(plant_dal: PlantDAL = Depends(get_plant_dal)):
    """Get pollen containers plus plants without pollen containers."""
    pollen_containers = await read_pollen_containers(plant_dal=plant_dal)
    plants_without_pollen_containers = await read_plants_without_pollen_containers(
        plant_dal=plant_dal
    )
    return {
        "pollenContainerCollection": pollen_containers,
        "plantsWithoutPollenContainerCollection": plants_without_pollen_containers,
    }


@router.post("/pollen_containers")
async def post_pollen_containers(
    pollen_containers_data: FRequestPollenContainers,
    plant_dal: PlantDAL = Depends(get_plant_dal),
):
    """Update pollen containers and add new ones."""
    await update_pollen_containers(
        pollen_containers_data=pollen_containers_data.pollenContainerCollection,
        plant_dal=plant_dal,
    )


@router.delete("/pollinations/{pollination_id}")
async def delete_pollination(
    pollination: Pollination = Depends(valid_pollination),
    pollination_dal=Depends(get_pollination_dal),
):
    await remove_pollination(pollination, pollination_dal=pollination_dal)


@router.post(
    "/retrain_probability_pollination_to_seed_model",
    response_model=BResultsRetrainingPollinationToSeedsModel,
)
async def retrain_probability_pollination_to_seed_model():
    """Retrain the probability_pollination_to_seed ml model."""
    return await train_model_for_probability_of_seed_production()


@router.get("/active_florescences", response_model=BResultsActiveFlorescences)
async def get_active_florescences(
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
):
    """Read active florescences, either after inflorescence appeared or flowering."""
    florescences = await read_active_florescences(
        florescence_dal=florescence_dal, pollination_dal=pollination_dal
    )
    return {
        "action": "Get active florescences",
        "message": get_message(f"Provided {len(florescences)} active florescences."),
        "activeFlorescenceCollection": florescences,
    }


@router.get(
    "/plants_for_new_florescence", response_model=BResultsPlantsForNewFlorescence
)
async def get_plants_for_new_florescence(plant_dal: PlantDAL = Depends(get_plant_dal)):
    """Read all plants available for new florescence."""
    plants = await read_plants_for_new_florescence(plant_dal=plant_dal)
    return {"plantsForNewFlorescenceCollection": plants}


@router.put(
    "/active_florescences/{florescence_id}"
)  # no response required (full reload after post)
async def put_active_florescence(
    edited_florescence_data: FlorescenceUpdate,
    florescence: Florescence = Depends(valid_florescence),
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
):
    if not florescence.id == edited_florescence_data.id:
        raise HTTPException(
            status_code=400,
            detail=f"florescence_id {florescence.id} does not match "
            f"florescence_id {edited_florescence_data.id} in request body.",
        )
    await update_active_florescence(
        florescence,
        edited_florescence_data=edited_florescence_data,
        florescence_dal=florescence_dal,
    )


@router.post("/active_florescences")  # no response required (full reload after post)
async def post_active_florescence(
    new_florescence_data: FlorescenceCreate,
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
):
    """Create new florescence for a plant."""
    await create_new_florescence(
        new_florescence_data=new_florescence_data,
        florescence_dal=florescence_dal,
        plant_dal=plant_dal,
    )


@router.delete("/florescences/{florescence_id}")
async def delete_florescence(
    florescence: Florescence = Depends(valid_florescence),
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
):
    await remove_florescence(florescence, florescence_dal=florescence_dal)


@router.get(
    "/potential_pollen_donors/{florescence_id}",
    response_model=BResultsPotentialPollenDonors,
)
async def get_potential_pollen_donors(
    florescence: Florescence = Depends(valid_florescence),
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
):
    potential_pollen_donors = await read_potential_pollen_donors(
        florescence=florescence,
        florescence_dal=florescence_dal,
        pollination_dal=pollination_dal,
        plant_dal=plant_dal,
    )
    return {
        "action": "Get potential pollen donors",
        "message": get_message(
            f"Provided {len(potential_pollen_donors)} potential donors."
        ),
        "potentialPollenDonorCollection": potential_pollen_donors,
    }


@router.get("/flower_history", response_model=BResultsFlowerHistory)
async def get_flower_history(
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
):
    months, flower_history = await generate_flower_history(
        florescence_dal=florescence_dal
    )
    return {
        "action": "Generate flower history",
        "message": get_message(f"Generated flower history for {len(months)} months."),
        "plants": flower_history,
        "months": months,
    }

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from plants.dependencies import (
    get_event_dal,
    get_florescence_dal,
    get_plant_dal,
    get_pollination_dal,
    get_seed_planting_dal,
    get_taxon_dal,
    valid_florescence,
    valid_pollination,
    valid_seed_planting,
)
from plants.modules.event.event_dal import EventDAL
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.plant.services import generate_plant_name_proposal_for_seed_planting
from plants.modules.pollination.enums import COLORS_MAP, PollinationStatus
from plants.modules.pollination.florescence_dal import FlorescenceDAL
from plants.modules.pollination.florescence_services import (
    create_new_florescence,
    read_active_florescences,
    read_plants_for_new_florescence,
    remove_florescence,
    update_active_florescence,
)
from plants.modules.pollination.flower_history_services import (
    generate_flower_history,
)
from plants.modules.pollination.models import Florescence, Pollination, SeedPlanting
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.pollination.pollination_services import (
    add_existing_same_taxon_plants_to_potential_pollinations,
    get_predicted_ripening_days,
    get_probability_pollination_to_seed,
    read_plants_without_pollen_containers,
    read_pollen_containers,
    read_pollinations,
    read_potential_pollen_donors,
    remove_pollination,
    save_new_pollination,
    update_pollen_containers,
    update_pollination,
)
from plants.modules.pollination.prediction.train_florescence import (
    train_model_for_florescence_probability,
)
from plants.modules.pollination.prediction.train_germination import (
    train_model_for_germination_days,
    train_model_for_germination_probability,
)
from plants.modules.pollination.prediction.train_pollination import (
    train_model_for_probability_of_seed_production,
)
from plants.modules.pollination.prediction.train_ripening import train_model_for_ripening_days
from plants.modules.pollination.schemas import (
    BResponsePredictProbabilityPollinationToSeed,
    BResultsActiveFlorescences,
    BResultsPlantsForNewFlorescence,
    BResultsPollenContainers,
    BResultsPotentialPollenDonors,
    BResultsRetrainingFlorescenceProbability,
    BResultsRetrainingGerminationDays,
    BResultsRetrainingGerminationProbability,
    BResultsRetrainingPollinationToSeedsModel,
    BResultsRetrainingRipeningDays,
    CreatePlantFromSeedPlantingRequest,
    CreateUpdatePollenContainersRequest,
    FlorescenceCreate,
    FlorescenceUpdate,
    FlowerHistory,
    GetPollinationsResponse,
    PollinationCreate,
    PollinationRead,
    PollinationUpdate,
    RequestPredictProbabilityPollinationToSeed,
    SeedPlantingCreate,
    SeedPlantingPlantNameProposal,
    SeedPlantingUpdate,
    SettingsRead,
)
from plants.modules.pollination.seed_planting_dal import SeedPlantingDAL
from plants.modules.pollination.seed_planting_services import (
    create_new_plant_for_seed_planting,
    remove_seed_planting,
    save_new_seed_planting,
    update_seed_planting,
)
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.message_services import get_message

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
) -> Any:
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
) -> Any:
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


@router.get("/ongoing_pollinations", response_model=GetPollinationsResponse)
async def get_ongoing_pollinations(
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
    *,
    include_ongoing_pollinations: bool = True,
    include_recently_finished_pollinations: bool = True,
    include_finished_pollinations: bool = False,
) -> Any:
    pollinations_orm = await read_pollinations(
        pollination_dal=pollination_dal,
        include_ongoing_pollinations=include_ongoing_pollinations,
        include_recently_finished_pollinations=include_recently_finished_pollinations,
        include_finished_pollinations=include_finished_pollinations,
    )

    # add predicted ripening days
    pollinations: list[PollinationRead] = []
    for p in pollinations_orm:
        pollination = PollinationRead.model_validate(p)
        pollination.florescence_status = p.florescence.florescence_status
        # if pollination.pollination_status == PollinationStatus.SEED_CAPSULE:
        pollination.predicted_ripening_days = get_predicted_ripening_days(p)

        # for clarity reasons we show the probability even if pollination already proved to be successful
        if pollination.pollination_status in (
            PollinationStatus.ATTEMPT,
            PollinationStatus.SEED_CAPSULE,
        ):
            pollination.probability_pollination_to_seed = get_probability_pollination_to_seed(
                florescence=p.florescence,
                pollen_donor=p.pollen_donor_plant,
                pollen_type=p.pollen_type,
            )

        # for sorting in the frontend, we look at all the pollinations with the same
        # florecence_id and take the minimum current_ripening_days
        pollination.florescence_min_current_ripening_days = min(
            [
                pp.current_ripening_days
                for pp in p.florescence.pollinations
                if pp.current_ripening_days is not None
            ]
        )

        pollinations.append(pollination)

    return {
        "action": "Get pollinations",
        "message": get_message(f"Provided {len(pollinations)} pollinations."),
        "ongoing_pollination_collection": pollinations,
    }


@router.get("/pollinations/settings", response_model=SettingsRead)
async def get_pollination_settings() -> Any:
    colors = list(COLORS_MAP.keys())
    return {
        "colors": colors,
    }


@router.get("/pollen_containers", response_model=BResultsPollenContainers)
async def get_pollen_containers(plant_dal: PlantDAL = Depends(get_plant_dal)) -> Any:
    """Get pollen containers plus plants without pollen containers."""
    pollen_containers = await read_pollen_containers(plant_dal=plant_dal)
    plants_without_pollen_containers = await read_plants_without_pollen_containers(
        plant_dal=plant_dal
    )
    return {
        "pollen_container_collection": pollen_containers,
        "plants_without_pollen_container_collection": plants_without_pollen_containers,
    }


@router.post("/pollen_containers")
async def post_pollen_containers(
    pollen_containers_data: CreateUpdatePollenContainersRequest,
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    """Update pollen containers and add new ones."""
    await update_pollen_containers(
        pollen_containers_data=pollen_containers_data.pollen_container_collection,
        plant_dal=plant_dal,
    )


@router.delete("/pollinations/{pollination_id}")
async def delete_pollination(
    pollination: Pollination = Depends(valid_pollination),
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
) -> Any:
    await remove_pollination(pollination, pollination_dal=pollination_dal)


@router.post(
    "/retrain_probability_pollination_to_seed_model",
    response_model=BResultsRetrainingPollinationToSeedsModel,
)
async def retrain_probability_pollination_to_seed_model() -> dict[str, str | float]:
    """Retrain the probability_pollination_to_seed ml model."""
    return await train_model_for_probability_of_seed_production()


@router.post(
    "/retrain_ripening_days",
    response_model=BResultsRetrainingRipeningDays,
)
async def retrain_ripening_days_model() -> dict[str, str | float]:
    """Retrain the ripening_days ml model."""
    return await train_model_for_ripening_days()


@router.post(
    "/retrain_germination_days_model",
    response_model=BResultsRetrainingGerminationDays,
)
async def retrain_germination_days_model() -> dict[str, str | float]:
    """Retrain the ripening_days ml model."""
    return await train_model_for_germination_days()


@router.post(
    "/retrain_germination_probability_model",
    response_model=BResultsRetrainingGerminationProbability,
)
async def retrain_germination_probability_model() -> dict[str, str | float]:
    """Retrain the ripening_days ml model."""
    return await train_model_for_germination_probability()


@router.post(
    "/retrain_florescence_probability_model",
    response_model=BResultsRetrainingFlorescenceProbability,
)
async def retrain_florescence_probability_model() -> dict[str, str | float]:
    """Retrain the florescence_probability ml model."""
    return await train_model_for_florescence_probability()


@router.get(
    "/seed_plantings/{seed_planting_id}/plant_name_proposal",
    response_model=SeedPlantingPlantNameProposal,
)
async def propose_plant_name_for_seed_planting(
    seed_planting: SeedPlanting = Depends(valid_seed_planting),
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    """Read active florescences, either after inflorescence appeared or flowering."""
    plant_name = await generate_plant_name_proposal_for_seed_planting(
        seed_planting=seed_planting, plant_dal=plant_dal
    )
    return {"plant_name_proposal": plant_name}


@router.post("/seed_plantings/{seed_planting_id}/plants")
async def post_new_plant_for_seed_planting(
    new_plant_info: CreatePlantFromSeedPlantingRequest,
    seed_planting: SeedPlanting = Depends(valid_seed_planting),
    plant_dal: PlantDAL = Depends(get_plant_dal),
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
    event_dal: EventDAL = Depends(get_event_dal),
) -> Any:
    """Read active florescences, either after inflorescence appeared or flowering."""
    await create_new_plant_for_seed_planting(
        seed_planting=seed_planting,
        plant_name=new_plant_info.plant_name,
        plant_dal=plant_dal,
        taxon_dal=taxon_dal,
        event_dal=event_dal,
    )


@router.post("/seed_plantings")
async def post_seed_planting(
    new_seed_planting_data: SeedPlantingCreate,
    seed_planting_dal: SeedPlantingDAL = Depends(get_seed_planting_dal),
) -> Any:
    await save_new_seed_planting(
        new_seed_planting_data=new_seed_planting_data,
        seed_planting_dal=seed_planting_dal,
    )


@router.delete("/seed_plantings/{seed_planting_id}")
async def delete_seed_planting(
    seed_planting: SeedPlanting = Depends(valid_seed_planting),
    seed_planting_dal: SeedPlantingDAL = Depends(get_seed_planting_dal),
) -> Any:
    await remove_seed_planting(seed_planting, seed_planting_dal=seed_planting_dal)


@router.put("/seed_plantings/{seed_planting_id}")  # no response required (full reload after post)
async def put_seed_planting(
    edited_seed_planting_data: SeedPlantingUpdate,
    seed_planting: SeedPlanting = Depends(valid_seed_planting),
    seed_planting_dal: SeedPlantingDAL = Depends(get_seed_planting_dal),
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
) -> Any:
    if not seed_planting.id == edited_seed_planting_data.id:
        raise HTTPException(
            status_code=400,
            detail=f"Seed Planting ID {seed_planting.id} does not match "
            f"ID {edited_seed_planting_data.id} in request body.",
        )
    await update_seed_planting(
        seed_planting,
        edited_seed_planting_data=edited_seed_planting_data,
        seed_planting_dal=seed_planting_dal,
        pollination_dal=pollination_dal,
    )


@router.get("/active_florescences", response_model=BResultsActiveFlorescences)
async def get_active_florescences(
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
) -> Any:
    """Read active florescences, either after inflorescence appeared or flowering."""
    florescences = await read_active_florescences(
        florescence_dal=florescence_dal,
        pollination_dal=pollination_dal,
    )
    return {
        "action": "Get active florescences",
        "message": get_message(f"Provided {len(florescences)} active florescences."),
        "active_florescence_collection": florescences,
    }


@router.get("/plants_for_new_florescence", response_model=BResultsPlantsForNewFlorescence)
async def get_plants_for_new_florescence(
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    """Read all plants available for new florescence."""
    plants = await read_plants_for_new_florescence(plant_dal=plant_dal)
    return {"plants_for_new_florescence_collection": plants}


@router.put(
    "/active_florescences/{florescence_id}"
)  # no response required (full reload after post)
async def put_active_florescence(
    edited_florescence_data: FlorescenceUpdate,
    florescence: Florescence = Depends(valid_florescence),
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
) -> Any:
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
) -> Any:
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
) -> Any:
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
) -> Any:
    potential_pollen_donors = await read_potential_pollen_donors(
        florescence=florescence,
        florescence_dal=florescence_dal,
        pollination_dal=pollination_dal,
        plant_dal=plant_dal,
    )
    await add_existing_same_taxon_plants_to_potential_pollinations(
        florescence=florescence,
        potential_pollen_donors=potential_pollen_donors,
        plant_dal=plant_dal,
    )
    return {
        "action": "Get potential pollen donors",
        "message": get_message(f"Provided {len(potential_pollen_donors)} potential donors."),
        "potential_pollen_donor_collection": potential_pollen_donors,
    }


@router.get(
    "/probability_pollination_to_seed",
    response_model=BResponsePredictProbabilityPollinationToSeed,
)
async def predict_probability_pollination_to_seed(
    # todo use many more properties for prediction
    predict_probability_pollination_to_seed_data: RequestPredictProbabilityPollinationToSeed = Depends(),
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    # Example:
    # http://localhost:5000/api/probability_pollination_to_seed?florescence_id=304&pollen_donor_plant_id=1085&pollen_type=fresh

    florescence = await florescence_dal.by_id(
        predict_probability_pollination_to_seed_data.florescence_id
    )
    pollen_donor = await plant_dal.by_id(
        predict_probability_pollination_to_seed_data.pollen_donor_plant_id
    )

    probability = get_probability_pollination_to_seed(
        florescence=florescence,
        pollen_donor=pollen_donor,
        pollen_type=predict_probability_pollination_to_seed_data.pollen_type,
    )
    return {
        "action": "Predict probability of pollination to seed",
        "message": get_message(f"Predicted probability: {probability}"),
        "probability_pollination_to_seed": probability,
    }


@router.get("/flower_history", response_model=FlowerHistory)
async def get_flower_history(
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
    *,
    include_inactive_plants: bool,
) -> Any:
    flower_history_rows = await generate_flower_history(
        florescence_dal=florescence_dal, include_inactive_plants=include_inactive_plants
    )
    return {
        "action": "Generate flower history",
        "message": get_message(f"Generated flower history with {len(flower_history_rows)} rows."),
        "rows": flower_history_rows,
    }

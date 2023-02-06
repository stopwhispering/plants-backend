import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from plants.modules.pollination.models import COLORS_MAP, Pollination, Florescence
from plants.modules.pollination.ml_model import train_model_for_probability_of_seed_production
from plants.modules.pollination.pollination_services import (save_new_pollination, read_ongoing_pollinations,
                                                             update_pollination,
                                                             read_pollen_containers, update_pollen_containers,
                                                             read_plants_without_pollen_containers, remove_pollination,
                                                             read_potential_pollen_donors)
from plants.modules.pollination.schemas import (BResultsOngoingPollinations,
                                                FRequestNewPollination,
                                                BResultsSettings, FRequestEditedPollination,
                                                BResultsPollenContainers, FRequestPollenContainers,
                                                BResultsRetrainingPollinationToSeedsModel, BResultsActiveFlorescences,
                                                BResultsPotentialPollenDonors, FRequestEditedFlorescence,
                                                BResultsPlantsForNewFlorescence, FRequestNewFlorescence,
                                                BResultsFlowerHistory, )
from plants.modules.pollination.florescence_services import (
    read_active_florescences, update_active_florescence, read_plants_for_new_florescence, create_new_florescence,
    remove_florescence)
from plants.modules.pollination.flower_history_services import generate_flower_history
from plants.shared.message_services import get_message
from plants.dependencies import get_db, valid_pollination, valid_florescence

logger = logging.getLogger(__name__)

router = APIRouter(
    # prefix="/pollination",
    tags=["pollination", "inflorence"],
    responses={404: {"description": "Not found"}},
)


@router.post('/pollinations')
async def post_pollination(
        new_pollination_data: FRequestNewPollination,
        db: Session = Depends(get_db)):
    save_new_pollination(new_pollination_data=new_pollination_data, db=db)
    db.commit()


@router.put('/pollinations/{pollination_id}')
async def put_pollination(
        edited_pollination_data: FRequestEditedPollination,
        pollination: Pollination = Depends(valid_pollination),
        db: Session = Depends(get_db), ):
    assert pollination.id == edited_pollination_data.id
    update_pollination(pollination, pollination_data=edited_pollination_data)
    db.commit()


@router.get("/ongoing_pollinations",
            response_model=BResultsOngoingPollinations)
async def get_ongoing_pollinations(db: Session = Depends(get_db)):
    ongoing_pollinations = read_ongoing_pollinations(db=db)
    return {'action': 'Get ongoing pollinations',
            'message': get_message(f"Provided {len(ongoing_pollinations)} ongoing pollinations."),
            'ongoingPollinationCollection': ongoing_pollinations}


@router.get("/pollinations/settings",
            response_model=BResultsSettings)
async def get_pollination_settings():
    colors = list(COLORS_MAP.keys())
    return {
        'colors': colors,
    }


@router.get("/pollen_containers",
            response_model=BResultsPollenContainers)
async def get_pollen_containers(db: Session = Depends(get_db)):
    """Get pollen containers plus plants without pollen containers """
    pollen_containers = read_pollen_containers(db=db)
    plants_without_pollen_containers = read_plants_without_pollen_containers(db=db)
    return {'pollenContainerCollection': pollen_containers,
            'plantsWithoutPollenContainerCollection': plants_without_pollen_containers}


@router.post("/pollen_containers")
async def post_pollen_containers(pollen_containers_data: FRequestPollenContainers,
                                 db: Session = Depends(get_db)):
    """update pollen containers and add new ones"""
    update_pollen_containers(pollen_containers_data=pollen_containers_data.pollenContainerCollection, db=db)
    db.commit()


@router.delete('/pollinations/{pollination_id}')
async def delete_pollination(
        pollination: Pollination = Depends(valid_pollination),
        db: Session = Depends(get_db)):
    remove_pollination(pollination, db=db)
    db.commit()


@router.post('/retrain_probability_pollination_to_seed_model',
             response_model=BResultsRetrainingPollinationToSeedsModel)
async def retrain_probability_pollination_to_seed_model(db: Session = Depends(get_db)):
    """retrain the probability_pollination_to_seed ml model"""
    results = train_model_for_probability_of_seed_production(db=db)
    return results


@router.get("/active_florescences", response_model=BResultsActiveFlorescences)
async def get_active_florescences(db: Session = Depends(get_db), ):
    """read active florescences, either after inflorescence appeared or flowering"""
    florescences = read_active_florescences(db)
    return {'action': 'Get active florescences',
            'message': get_message(f"Provided {len(florescences)} active florescences."),
            'activeFlorescenceCollection': florescences}


@router.get("/plants_for_new_florescence", response_model=BResultsPlantsForNewFlorescence)
async def get_plants_for_new_florescence(db: Session = Depends(get_db), ):
    """read all plants available for new florescence"""
    plants = read_plants_for_new_florescence(db)
    return {'plantsForNewFlorescenceCollection': plants}


@router.put('/active_florescences/{florescence_id}')  # no response required (full reload after post)
async def put_active_florescence(
        edited_florescence_data: FRequestEditedFlorescence,
        florescence: Florescence = Depends(valid_florescence),
        db: Session = Depends(get_db)):
    assert florescence.id == edited_florescence_data.id
    update_active_florescence(florescence, edited_florescence_data=edited_florescence_data)
    db.commit()


@router.post("/active_florescences")  # no response required (full reload after post)
async def post_active_florescence(new_florescence_data: FRequestNewFlorescence,
                                  db: Session = Depends(get_db), ):
    """create new florescence for a plant"""
    create_new_florescence(new_florescence_data=new_florescence_data, db=db)
    db.commit()


@router.delete('/florescences/{florescence_id}')
async def delete_florescence(
        florescence: Florescence = Depends(valid_florescence),
        db: Session = Depends(get_db), ):
    remove_florescence(florescence, db=db)
    db.commit()


@router.get("/potential_pollen_donors/{florescence_id}",
            response_model=BResultsPotentialPollenDonors)
async def get_potential_pollen_donors(florescence: Florescence = Depends(valid_florescence),
                                      db: Session = Depends(get_db), ):
    potential_pollen_donors = read_potential_pollen_donors(florescence=florescence, db=db)
    return {'action': 'Get potential pollen donors',
            'message': get_message(f"Provided {len(potential_pollen_donors)} potential donors."),
            'potentialPollenDonorCollection': potential_pollen_donors}


@router.get("/flower_history",
            response_model=BResultsFlowerHistory)
async def get_flower_history(db: Session = Depends(get_db), ):
    months, flower_history = generate_flower_history(db=db)
    return {'action': 'Generate flower history',
            'message': get_message(f"Generated flower history for {len(months)} months."),
            'plants': flower_history,
            'months': months}

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging
import datetime

from plants.models.pollination_models import COLORS_MAP, PollinationStatus
from plants.services.pollination_services import (save_new_pollination, read_ongoing_pollinations, update_pollination,
                                                  read_pollen_containers, update_pollen_containers,
                                                  read_plants_without_pollen_containers)
from plants.util.ui_utils import (get_message)
from plants.dependencies import get_db
from plants.validation.pollination_validation import (PResultsOngoingPollinations,
                                                      PRequestNewPollination,
                                                      PResultsSettings, PRequestEditedPollination,
                                                      PResultsPollenContainers, PRequestPollenContainers)

logger = logging.getLogger(__name__)

NULL_DATE = datetime.date(1900, 1, 1)

router = APIRouter(
    # prefix="/pollination",
    tags=["pollination", "inflorence"],
    responses={404: {"description": "Not found"}},
)


@router.post('/pollinations')
async def post_pollination(
        new_pollination_data: PRequestNewPollination,
        db: Session = Depends(get_db)):
    save_new_pollination(new_pollination_data=new_pollination_data, db=db)


@router.put('/pollinations/{pollination_id}')
async def put_pollination(
        pollination_id: int,
        edited_pollination_data: PRequestEditedPollination,
        db: Session = Depends(get_db)):
    assert pollination_id == edited_pollination_data.id
    update_pollination(pollination_data=edited_pollination_data, db=db)


@router.get("/ongoing_pollinations",
            response_model=PResultsOngoingPollinations)
async def get_ongoing_pollinations(db: Session = Depends(get_db)):
    ongoing_pollinations = read_ongoing_pollinations(db=db)

    results = {'action': 'Get ongoing pollinations',
               'message': get_message(f"Provided {len(ongoing_pollinations)} ongoing pollinations."),
               'ongoingPollinationCollection': ongoing_pollinations}
    return results


@router.get("/pollinations/settings",
            response_model=PResultsSettings)
async def get_pollination_settings():
    colors = list(COLORS_MAP.keys())
    pollination_status = [
        {'key': PollinationStatus.ATTEMPT.value, 'text': 'Attempt'},
        {'key': PollinationStatus.SEED_CAPSULE.value, 'text': 'Capsule'},
        {'key': PollinationStatus.SEED.value, 'text': 'Seed'},
        {'key': PollinationStatus.GERMINATED.value, 'text': 'Plant'},
    ]

    results = {'colors': colors,
               'pollination_status': pollination_status}
    return results


@router.get("/pollen_containers",
            response_model=PResultsPollenContainers)
async def get_pollen_containers(db: Session = Depends(get_db)):
    """Get pollen containers plus plants without pollen containers """
    pollen_containers = read_pollen_containers(db=db)
    plants_without_pollen_containers = read_plants_without_pollen_containers(db=db)
    results = {'pollenContainerCollection': pollen_containers,
               'plantsWithoutPollenContainerCollection': plants_without_pollen_containers}
    return results


@router.post("/pollen_containers")
async def post_pollen_containers(pollen_containers_data: PRequestPollenContainers,
                                 db: Session = Depends(get_db)):
    """update pollen containers and add new ones"""
    update_pollen_containers(pollen_containers_data=pollen_containers_data.pollenContainerCollection, db=db)


@router.put('/pollinations/{pollination_id}')
async def put_pollination(
        pollination_id: int,
        edited_pollination_data: PRequestEditedPollination,
        db: Session = Depends(get_db)):
    assert pollination_id == edited_pollination_data.id
    update_pollination(pollination_data=edited_pollination_data, db=db)

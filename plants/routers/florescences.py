from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging
import datetime

from plants.services.florescence_services import read_active_florescences, update_active_florescence, \
    read_plants_for_new_florescence, create_new_florescence, remove_florescence
from plants.services.pollination_services import read_potential_pollen_donors
from plants.util.ui_utils import (get_message)
from plants.dependencies import get_db
from plants.validation.pollination_validation import (PResultsActiveFlorescences,
                                                      PResultsPotentialPollenDonors, PRequestEditedFlorescence,
                                                      PResultsPlantsForNewFlorescence, PRequestNewFlorescence,
                                                      )

logger = logging.getLogger(__name__)

NULL_DATE = datetime.date(1900, 1, 1)

router = APIRouter(
    # prefix="/pollination",
    tags=["pollination", "inflorence"],
    responses={404: {"description": "Not found"}},
)


@router.get("/active_florescences", response_model=PResultsActiveFlorescences)
async def get_active_florescences(db: Session = Depends(get_db),):
    """read active florescences, either after inflorescence appeared or flowering"""
    florescences = read_active_florescences(db)

    results = {'action': 'Get active florescences',
               'message': get_message(f"Provided {len(florescences)} active florescences."),
               'activeFlorescenceCollection': florescences}

    return results


@router.get("/plants_for_new_florescence", response_model=PResultsPlantsForNewFlorescence)
async def get_active_florescences(db: Session = Depends(get_db),):
    """read all plants available for new florescence"""
    plants = read_plants_for_new_florescence(db)
    results = {'plantsForNewFlorescenceCollection': plants}
    return results


@router.put('/active_florescences/{florescence_id}')
async def put_active_florescence(
        florescence_id: int,
        edited_florescence_data: PRequestEditedFlorescence,
        db: Session = Depends(get_db)):
    assert florescence_id == edited_florescence_data.id

    update_active_florescence(edited_florescence_data=edited_florescence_data, db=db)


@router.post("/active_florescences")
async def post_active_florescence(new_florescence_data: PRequestNewFlorescence,
                                  db: Session = Depends(get_db),):
    """create new florescence for a plant"""
    create_new_florescence(new_florescence_data=new_florescence_data, db=db)


@router.delete('/florescences/{florescence_id}')
async def delete_florescence(
        florescence_id: int,
        db: Session = Depends(get_db),):
    remove_florescence(florescence_id=florescence_id, db=db)



@router.get("/potential_pollen_donors/{florescence_id}",
            response_model=PResultsPotentialPollenDonors)
async def get_potential_pollen_donors(florescence_id: int,
                                      db: Session = Depends(get_db),):
    potential_pollen_donors = read_potential_pollen_donors(florescence_id=florescence_id, db=db)

    results = {'action': 'Get potential pollen donors',
               'message': get_message(f"Provided {len(potential_pollen_donors)} potential donors."),
               'potentialPollenDonorCollection': potential_pollen_donors}
    return results

from collections import defaultdict

from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session

from plants.shared.message_services import get_message
from plants.dependencies import get_db, valid_plant
from plants.modules.event.services import create_soil, update_soil, read_events_for_plant, create_or_update_event, \
    fetch_soils
from plants.shared.message_schemas import BMessageType, FBMajorResource, BSaveConfirmation
from plants.modules.plant.models import Plant
from plants.modules.event.schemas import (BResultsEventResource, BPResultsUpdateCreateSoil,
                                          BResultsSoilsResource, FSoilCreate, FRequestCreateOrUpdateEvent, FSoil)

logger = logging.getLogger(__name__)

router = APIRouter(
    # prefix="/events",
    tags=["events"],
    responses={404: {"description": "Not found"}},
)


@router.get("/events/soils", response_model=BResultsSoilsResource)
async def get_soils(db: Session = Depends(get_db)):
    soils = fetch_soils(db=db)
    return {'SoilsCollection': soils}


@router.post("/events/soils", response_model=BPResultsUpdateCreateSoil)
async def create_new_soil(new_soil: FSoilCreate, db: Session = Depends(get_db)):
    """create new soil and return it with (newly assigned) id"""
    soil = create_soil(soil=new_soil, db=db)

    logger.info(msg := f'Created soil with new ID {soil.id}')
    return {'soil': soil,
            'message': get_message(msg, message_type=BMessageType.DEBUG)}


@router.put("/events/soils", response_model=BPResultsUpdateCreateSoil)
async def update_existing_soil(updated_soil: FSoil, db: Session = Depends(get_db)):
    """update soil attributes"""
    soil = update_soil(soil=updated_soil, db=db)

    logger.info(msg := f'Updated soil with ID {soil.id}')
    return {'soil': soil.as_dict(),
            'message': get_message(msg, message_type=BMessageType.DEBUG)}


@router.get("/events/{plant_id}", response_model=BResultsEventResource)
async def get_events(plant: Plant = Depends(valid_plant)):
    """
    returns events from event database table
    """
    events = read_events_for_plant(plant)

    logger.info(msg := f'Receiving {len(events)} events for {plant.plant_name}.')
    return {'events': events,
            'message': get_message(msg,
                                   message_type=BMessageType.DEBUG)}


@router.post("/events/", response_model=BSaveConfirmation)
async def create_or_update_events(events_request: FRequestCreateOrUpdateEvent,
                                  db: Session = Depends(get_db)):
    """save n events for n plants in database (add, modify, delete)"""
    # frontend submits a dict with events for those plants where at least one event has been changed, added, or
    # deleted. it does, however, always submit all these plants' events

    # loop at the plants and their events, identify additions, deletions, and updates and save them
    counts = defaultdict(int)
    for plant_id, events in events_request.plants_to_events.items():
        create_or_update_event(plant_id=plant_id, events=events, counts=counts, db=db)

    db.commit()

    logger.info(' Saving Events: ' + (description := ', '.join([f'{key}: {counts[key]}' for key in counts.keys()])))
    results = {'resource': FBMajorResource.EVENT,
               'message': get_message(f'Updated events in database.',
                                      description=description)}

    return results

from operator import attrgetter
from collections import defaultdict

from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session, subqueryload

from plants.util.ui_utils import get_message
from plants.dependencies import get_db
from plants.services.event_services import create_soil, update_soil, read_events_for_plant, create_or_update_event
from plants.validation.message_validation import BMessageType, FBMajorResource, BSaveConfirmation
from plants.models.plant_models import Plant
from plants.models.event_models import Soil
from plants.validation.event_validation import (BResultsEventResource, BPResultsUpdateCreateSoil,
                                                BResultsSoilsResource, FSoilCreate, FRequestCreateOrUpdateEvent, FSoil)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={404: {"description": "Not found"}},
)


@router.get("/soils", response_model=BResultsSoilsResource)
async def get_soils(db: Session = Depends(get_db)):
    soils = []

    # add the number of plants that currently have a specific soil
    soil_counter = defaultdict(int)

    plants = (db.query(Plant)
              .options(subqueryload(Plant.events))  # .subqueryload(Event.soil))
              .all())
    for plant in plants:
        # if events := [e for e in plant.events if e.soil_id]:
        if events := [e for e in plant.events if e.soil and e.soil.id]:
            latest_event = max(events, key=attrgetter('date'))
            # soil_counter[latest_event.soil_id] += 1
            soil_counter[latest_event.soil.id] += 1

    for soil in db.query(Soil).all():
        soil.plants_count = soil_counter.get(soil.id, 0)
        soils.append(soil)

    return {'SoilsCollection': soils}


@router.post("/soils", response_model=BPResultsUpdateCreateSoil)
async def create_new_soil(new_soil: FSoilCreate, db: Session = Depends(get_db)):
    """create new soil and return it with (newly assigned) id"""
    soil_obj = create_soil(soil=new_soil, db=db)
    msg = f'Created soil with new ID {soil_obj.id}'

    logger.info(msg)
    results = {'soil': soil_obj,  # soil_obj.as_dict(),
               'message': get_message(msg, message_type=BMessageType.DEBUG)}
    return results


@router.put("/soils", response_model=BPResultsUpdateCreateSoil)
async def update_existing_soil(updated_soil: FSoil, db: Session = Depends(get_db)):
    """update soil attributes"""
    soil_obj = update_soil(soil=updated_soil, db=db)
    msg = f'Updated soil with ID {soil_obj.id}'

    logger.info(msg)
    results = {'soil': soil_obj.as_dict(),
               'message': get_message(msg, message_type=BMessageType.DEBUG)}
    return results


@router.get("/{plant_id}", response_model=BResultsEventResource)
async def get_events(plant_id: int, db: Session = Depends(get_db)):
    """returns events from event database table
    imports: plant_id
    exports: see PResultsEventResource
    """
    results = read_events_for_plant(plant_id=plant_id, db=db)
    # event_objs = Event.get_events_by_plant_id(plant_id, db)
    # for event_obj in event_objs:
    #     results.append(event_obj.as_dict())

    logger.info(m := f'Receiving {len(results)} events for {Plant.get_plant_name_by_plant_id(plant_id, db)}.')
    results = {'events': results,
               'message': get_message(m,
                                      message_type=BMessageType.DEBUG)}

    return results


@router.post("/", response_model=BSaveConfirmation)
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

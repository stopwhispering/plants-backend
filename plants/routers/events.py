from operator import attrgetter
from typing import Optional
from collections import defaultdict

from sqlalchemy.exc import InvalidRequestError
from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session, subqueryload
from starlette.requests import Request

from plants.util.ui_utils import throw_exception, get_message, MessageType
from plants.dependencies import get_db
from plants.models.image_models import Image, ImageToEventAssociation
from plants.services.event_services import create_soil, update_soil
from plants.validation.message_validation import PConfirmation
from plants.models.plant_models import Plant
from plants.models.event_models import Pot, Observation, Event, Soil
from plants.validation.event_validation import (PResultsEventResource, PSoil, PResultsSoilResource,
                                                PResultsSoilsResource, PSoilCreate, PEventCreateOrUpdateRequest)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={404: {"description": "Not found"}},
)


@router.get("/soils", response_model=PResultsSoilsResource)
async def get_soils(db: Session = Depends(get_db)):
    soils = []

    # add the number of plants that currently have a specific soil
    soil_counter = defaultdict(int)

    plants = (db.query(Plant)
              .filter((Plant.hide.is_(False)) | (Plant.hide.is_(None)))
              .options(subqueryload(Plant.events))  # .subqueryload(Event.soil))
              .all())
    for plant in plants:
        if events := [e for e in plant.events if e.soil_id]:
            latest_event = max(events, key=attrgetter('date'))
            soil_counter[latest_event.soil_id] += 1

    for soil in db.query(Soil).all():
        soil.plants_count = soil_counter.get(soil.id, 0)
        soils.append(soil)

    return {'SoilsCollection': soils}


@router.post("/soils", response_model=PResultsSoilResource)
async def create_new_soil(new_soil: PSoilCreate, db: Session = Depends(get_db)):
    """create new soil and return it with (newly assigned) id"""
    soil_obj = create_soil(soil=new_soil, db=db)
    msg = f'Created soil with new ID {soil_obj.id}'

    logger.info(msg)
    results = {'soil': soil_obj,  # soil_obj.as_dict(),
               'message': get_message(msg, message_type=MessageType.DEBUG)}
    return results


@router.put("/soils", response_model=PResultsSoilResource)
async def update_existing_soil(updated_soil: PSoil, db: Session = Depends(get_db)):
    """update soil attributes"""
    soil_obj = update_soil(soil=updated_soil, db=db)
    msg = f'Updated soil with ID {soil_obj.id}'

    logger.info(msg)
    results = {'soil': soil_obj.as_dict(),
               'message': get_message(msg, message_type=MessageType.DEBUG)}
    return results


@router.get("/{plant_id}", response_model=PResultsEventResource)
async def get_events(plant_id: int, db: Session = Depends(get_db)):
    """returns events from event database table
    imports: plant_id
    exports: see PResultsEventResource
    """
    results = []
    # might be a newly created plant with no existing events, yet
    event_objs = Event.get_events_by_plant_id(plant_id, db)
    for event_obj in event_objs:
        results.append(event_obj.as_dict())

    logger.info(m := f'Receiving {len(results)} events for {Plant.get_plant_name_by_plant_id(plant_id, db)}.')
    results = {'events': results,
               'message': get_message(m,
                                      message_type=MessageType.DEBUG)}

    return results


@router.post("/", response_model=PConfirmation)
async def create_or_update_events(request: Request,
                                  # todo replace dict with ordinary pydantic schema (also on ui side)
                                  args: PEventCreateOrUpdateRequest,
                                  # plants_events_dict: Dict[int, List[PEventCreateOrUpdate]] = Body(..., embed=True),
                                  db: Session = Depends(get_db)):
    """save n events for n plants in database (add, modify, delete)"""
    # frontend submits a dict with events for those plants where at least one event has been changed, added, or
    # deleted. it does, however, always submit all these plants' events

    # loop at the plants and their events
    counts = defaultdict(int)
    new_list = []
    for plant_id, events in args.plants_to_events.items():

        # plant_obj = Plant.get_plant_by_plant_name(plant_name, db, raise_exception=True)
        plant_obj = Plant.get_plant_by_plant_id(plant_id, db, raise_exception=True)
        logger.info(f'Plant {plant_obj.plant_name} has {len(plant_obj.events)} events in db:'
                    f' {[e.id for e in plant_obj.events]}')

        # event might have no id in browser but already in backend from earlier save
        # so try to get eventid  from plant name and date (pseudo-key) to avoid events being deleted
        # note: if we "replace" an event in the browser  (i.e. for a specific date, we delete an event and
        # create a new one, then that event in database will be modified, not deleted and re-created
        for event in [e for e in events if not e.id]:

            event_obj_id = db.query(Event.id).filter(Event.plant_id == plant_obj.id,
                                                     Event.date == event.date).scalar()
            if event_obj_id is not None:
                event.id = event_obj_id
                logger.info(f"Identified event without id from browser as id {event.id}")
        event_ids = [e.id for e in events]
        logger.info(f'Updating {len(events)} events ({event_ids})for plant {plant_id}')

        # loop at the current plant's database events to find deleted ones
        event_obj: Optional[Event] = None
        for event_obj in plant_obj.events:
            if event_obj.id not in event_ids:
                logger.info(f'Deleting event {event_obj.id}')
                for link in event_obj.image_to_event_associations:
                    db.delete(link)
                db.delete(event_obj)
                counts['Deleted Events'] += 1

        # loop at the current plant's events from frontend to find new events and modify existing ones
        for event in events:
            # new event
            if not event.id:
                # create event record
                logger.info('Creating event.')
                event_obj = Event(date=event.date,
                                  event_notes=event.event_notes,
                                  plant=plant_obj
                                  )
                db.add(event_obj)
                counts['Added Events'] += 1

            # update existing event
            else:
                try:
                    logger.info(f'Getting event  {event.id}.')
                    event_obj = Event.get_event_by_event_id(event.id, db)
                    if not event_obj:
                        logger.warning(f'Event not found: {event.id}')
                        continue
                    event_obj.event_notes = event.event_notes
                    event_obj.date = event.date

                except InvalidRequestError as e:
                    db.rollback()
                    logger.error('Serious error occured at event resource (POST). Rollback. See log.',
                                 stack_info=True, exc_info=e)
                    throw_exception('Serious error occured at event resource (POST). Rollback. See log.',
                                    request=request)

            # segments observation, pot, and soil
            if event.observation and not event_obj.observation:
                observation_obj = Observation()
                db.add(observation_obj)
                event_obj.observation = observation_obj
                counts['Added Observations'] += 1
            elif not event.observation and event_obj.observation:
                # 1:1 relationship, so we can delete the observation directly
                db.delete(event_obj.observation)
                event_obj.observation = None
            if event.observation and event_obj.observation:
                event_obj.observation.diseases = event.observation.diseases
                event_obj.observation.observation_notes = event.observation.observation_notes
                # cm to mm
                event_obj.observation.height = event.observation.height * 10 if event.observation.height else None
                event_obj.observation.stem_max_diameter = event.observation.stem_max_diameter * 10 if \
                    event.observation.stem_max_diameter else None

            if not event.pot:
                event_obj.pot_event_type = None
                event_obj.pot = None

            else:
                event_obj.pot_event_type = event.pot_event_type
                # add empty if not existing
                if not event_obj.pot:
                    pot_obj = Pot()
                    db.add(pot_obj)
                    event_obj.pot = pot_obj
                    counts['Added Pots'] += 1

                # pot objects have an id but are not "reused" for other events, so we may change it here
                event_obj.pot.material = event.pot.material
                event_obj.pot.shape_side = event.pot.shape_side
                event_obj.pot.shape_top = event.pot.shape_top
                event_obj.pot.diameter_width = event.pot.diameter_width * 10 if event.pot.diameter_width else None

            # remove soil from event
            #  (event to soil is n:1 so we don't delete the soil object but only the assignment)
            if not event.soil:
                event_obj.soil_event_type = None
                if event_obj.soil:
                    event_obj.soil = None

            # add soil to event
            else:
                event_obj.soil_event_type = event.soil_event_type
                if not event.soil.id:
                    throw_exception(f"Can't update Soil {event.soil.soil_name} without ID.")
                if not event_obj.soil or (event.soil.id != event_obj.soil.id):
                    soil = db.query(Soil).filter(Soil.id == event.soil.id).first()
                    if not soil:
                        throw_exception(f'Soil ID {event.soil.id} not found')
                    event_obj.soil = soil
                    counts['Added Soils'] += 1

            # changes to images attached to the event
            # deleted images
            # path_originals_saved = [image.path_original for image in event.images] if event.images else []
            path_originals_saved = [image.relative_path for image in event.images] if event.images else []
            for image_obj in event_obj.images:
                image_obj: Image
                if image_obj.relative_path not in path_originals_saved:
                    # don't delete photo_file object, but only the association
                    # (photo_file might be assigned to other events)
                    li: ImageToEventAssociation
                    link: ImageToEventAssociation = next(li for li in event_obj.image_to_event_associations if
                                                         li.image.relative_path == image_obj.relative_path)
                    db.delete(link)

            # newly assigned images
            if event.images:
                for image in event.images:
                    image_obj = db.query(Image).filter(Image.relative_path == image.relative_path.as_posix()).scalar()
                    if not image_obj:
                        raise ValueError(f'Image not in db: {image.relative_path.as_posix()}')

                    # not assigned to that specific event, yet
                    if image_obj not in event_obj.images:
                        event_obj.images.append(image_obj)

    if new_list:
        db.add_all(new_list)
    db.commit()

    logger.info(' Saving Events: ' + (description := ', '.join([f'{key}: {counts[key]}' for key in counts.keys()])))
    results = {'action': 'Saved events',
               'resource': 'EventResource',
               'message': get_message(f'Updated events in database.',
                                      description=description)}

    return results

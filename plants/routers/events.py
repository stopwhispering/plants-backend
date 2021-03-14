from typing import Optional, Dict, List
from collections import defaultdict
from sqlalchemy.exc import InvalidRequestError
from fastapi import APIRouter, Depends, Body
import logging
from pydantic.error_wrappers import ValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request

from plants.util.ui_utils import throw_exception, get_message, MessageType
from plants.dependencies import get_db
from plants.models.image_models import Image
from plants.services.event_services import get_or_create_soil
from plants.validation.message_validation import PConfirmation
from plants.models.plant_models import Plant
from plants.models.event_models import Pot, Observation, Event
from plants.validation.event_validation import PResultsEventResource, PEventNew
from plants.validation.plant_validation import PPlantId

logger = logging.getLogger(__name__)

router = APIRouter(
        prefix="/events",
        tags=["events"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/{plant_id}", response_model=PResultsEventResource)
async def get_events(request: Request, plant_id: int, db: Session = Depends(get_db)):
    """returns events from event database table
    imports: plant_id
    exports: see PResultsEventResource
    """
    # evaluate arguments
    try:
        PPlantId.parse_obj(plant_id)
    except ValidationError:
        throw_exception('Plant ID required for GET requests', request=request)

    results = []
    # might be a newly created plant with no existing events, yet
    event_objs = Event.get_events_by_plant_id(plant_id, db)
    for event_obj in event_objs:
        results.append(event_obj.as_dict())

    logger.info(m := f'Receiving {len(results)} events for {Plant.get_plant_name_by_plant_id(plant_id, db)}.')
    results = {'events':  results,
               'message': get_message(m,
                                      message_type=MessageType.DEBUG)}

    return results


@router.post("/", response_model=PConfirmation)
async def modify_events(request: Request,
                        # todo replace dict with ordinary pydantic schema (also on ui side)
                        plants_events_dict: Dict[str, List[PEventNew]] = Body(..., embed=True),
                        db: Session = Depends(get_db)):
    """save n events for n plants in database (add, modify, delete)"""
    # frontend submits a dict with events for those plants where at least one event has been changed, added, or
    # deleted. it does, however, always submit all these plants' events

    # loop at the plants and their events
    counts = defaultdict(int)
    new_list = []
    for plant_name, events in plants_events_dict.items():

        plant_obj = Plant.get_plant_by_plant_name(plant_name, db, raise_exception=True)
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
        logger.info(f'Updating {len(events)} events ({event_ids})for plant {plant_name}')

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

            if not event.soil:
                event_obj.soil_event_type = None
                # remove soil from event (event to soil is n:1 so we don't delete the soil object but only the
                # assignment)
                if event_obj.soil:
                    event_obj.soil = None

            else:
                event_obj.soil_event_type = event.soil_event_type
                # add soil to event or change it
                if not event_obj.soil or (event.soil and event.soil.id != event_obj.soil.id):
                    event_obj.soil = get_or_create_soil(event.soil.dict(), counts, db)

            # changes to images attached to the event
            # deleted images
            path_originals_saved = [image.path_original for image in event.images] if event.images else []
            for image_obj in event_obj.images:
                if image_obj.relative_path not in path_originals_saved:
                    # don't delete image object, but only the association (image might be assigned to other events)
                    db.delete([link for link in event_obj.image_to_event_associations if
                               link.image.relative_path == image_obj.relative_path][0])

            # newly assigned images
            if event.images:
                for image in event.images:
                    image_obj = db.query(Image).filter(Image.relative_path == image.path_original).first()

                    # not assigned to any event, yet
                    if not image_obj:
                        image_obj = Image(relative_path=image.path_original)
                        new_list.append(image_obj)

                    # not assigned to that specific event, yet
                    if image_obj not in event_obj.images:
                        event_obj.images.append(image_obj)

    if new_list:
        db.add_all(new_list)
    db.commit()

    logger.info(' Saving Events: ' + (description := ', '.join([f'{key}: {counts[key]}' for key in counts.keys()])))
    results = {'action':   'Saved events',
               'resource': 'EventResource',
               'message':  get_message(f'Updated events in database.',
                                       description=description)}

    return results

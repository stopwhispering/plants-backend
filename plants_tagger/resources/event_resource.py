from typing import Optional
from flask_restful import Resource
import logging
from flask import request
from collections import defaultdict
from sqlalchemy.exc import InvalidRequestError
from flask_2_ui5_py import get_message, throw_exception, MessageType

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.plant_models import Plant
from plants_tagger.models.image_models import Image
from plants_tagger.models.event_models import Pot, Observation, Event
from plants_tagger.services.event_services import get_or_create_soil

logger = logging.getLogger(__name__)


class EventResource(Resource):
    @staticmethod
    def get(plant_name):
        """returns events from event database table; supply plant_name not id as new plants don't have an id, yet"""

        if not plant_name:
            throw_exception('Plant name required for GET requests')

        results = []
        # might be a newly created plant with no existing events, yet
        if plant_id := Plant.get_plant_id_by_plant_name(plant_name):
            event_objs = Event.get_events_by_plant_id(plant_id)
            for event_obj in event_objs:
                results.append(event_obj.as_dict())

        logger.info(f'Returning {len(results)} events for {plant_name}.')
        return {'events':  results,
                'message':  get_message(f'Returning {len(results)} events for {plant_name}.',
                                        message_type=MessageType.DEBUG)}

    @staticmethod
    def post():
        """save n events for n plants in database (add, modify, delete)"""
        # frontend submits a dict with events for those plants where at least one event has been changed, added, or
        # deleted. it does, however, always submit all these plants' events
        if not (plants_events_dict := request.get_json()['ModifiedEventsDict']):
            throw_exception('No plants and events supplied to save.')

        # loop at the plants and their events
        counts = defaultdict(int)
        new_list = []
        for plant_name, events in plants_events_dict.items():

            plant_obj = Plant.get_plant_by_plant_name(plant_name, raise_exception=True)
            logger.info(f'Plant {plant_obj.plant_name} has {len(plant_obj.events)} events in db:'
                        f' {[e.id for e in plant_obj.events]}')

            # event might have no id in browser but already in backend from earlier save
            # so try to get eventid  from plant name and date (pseudo-key) to avoid events being deleted
            # note: if we "replace" an event in the browser  (i.e. for a specific date, we delete an event and
            # create a new one, then that event in database will be modified, not deleted and re-created
            for event in [e for e in events if not e.get('id')]:

                event_obj_id = get_sql_session().query(Event.id).filter(Event.plant_id == plant_obj.id,
                                                                        Event.date == event.get('date')).scalar()
                if event_obj_id is not None:
                    event['id'] = event_obj_id
                    logger.info(f"Identified event without id from browser as id {event['id']}")
            event_ids = [e.get('id') for e in events]
            logger.info(f'Updating {len(events)} events ({event_ids})for plant {plant_name}')

            # loop at the current plant's database events to find deleted ones
            event_obj: Optional[Event] = None
            for event_obj in plant_obj.events:
                if event_obj.id not in event_ids:
                    logger.info(f'Deleting event {event_obj.id}')
                    for link in event_obj.image_to_event_associations:
                        get_sql_session().delete(link)
                    get_sql_session().delete(event_obj)
                    counts['Deleted Events'] += 1

            # loop at the current plant's events from frontend to find new events and modify existing ones
            for event in events:
                # new event
                if not event.get('id'):
                    # create event record
                    logger.info('Creating event.')
                    event_obj = Event(date=event.get('date'),
                                      event_notes=event.get('event_notes'),
                                      plant=plant_obj
                                      )
                    get_sql_session().add(event_obj)
                    counts['Added Events'] += 1

                # update existing event
                else:
                    try:
                        logger.info(f'Getting event  {event.get("id")}.')
                        event_obj = Event.get_event_by_event_id(event.get('id'))
                        if not event_obj:
                            logger.warning(f'Event not found: {event.get("id")}')
                            continue
                        event_obj.event_notes = event.get('event_notes')
                        event_obj.date = event.get('date')

                    except InvalidRequestError as e:
                        get_sql_session().rollback()
                        logger.error('Serious error occured at event resource (POST). Rollback. See log.',
                                     stack_info=True, exc_info=e)
                        throw_exception('Serious error occured at event resource (POST). Rollback. See log.')

                # segments observation, pot, and soil
                if 'observation' in event and not event_obj.observation:
                    observation_obj = Observation()
                    get_sql_session().add(observation_obj)
                    event_obj.observation = observation_obj
                    counts['Added Observations'] += 1
                elif 'observation' not in event and event_obj.observation:
                    # 1:1 relationship, so we can delete the observation directly
                    get_sql_session().delete(event_obj.observation)
                    event_obj.observation = None
                if 'observation' in event and event_obj.observation:
                    event_obj.observation.diseases = event['observation'].get('diseases')
                    event_obj.observation.observation_notes = event['observation'].get('observation_notes')
                    event_obj.observation.height = event['observation'].get('height') * 10 if event[
                        'observation'].get('height') else None  # cm to mm
                    event_obj.observation.stem_max_diameter = event['observation'].get('stem_max_diameter') * 10 if \
                        event['observation'].get('stem_max_diameter') else None

                if 'pot' not in event:
                    event_obj.pot_event_type = None
                    event_obj.pot = None

                else:
                    event_obj.pot_event_type = event.get('pot_event_type')
                    # add empty if not existing
                    if not event_obj.pot:
                        pot_obj = Pot()
                        get_sql_session().add(pot_obj)
                        event_obj.pot = pot_obj
                        counts['Added Pots'] += 1

                    # pot objects have an id but are not "reused" for other events, so we may change it here
                    event_obj.pot.material = event['pot'].get('material')
                    event_obj.pot.shape_side = event['pot'].get('shape_side')
                    event_obj.pot.shape_top = event['pot'].get('shape_top')
                    event_obj.pot.diameter_width = event['pot'].get('diameter_width') * 10 if event['pot'].get(
                            'diameter_width') else None

                if 'soil' not in event:
                    event_obj.soil_event_type = None
                    # remove soil from event (event to soil is n:1 so we don't delete the soil object but only the
                    # assignment)
                    if event_obj.soil:
                        event_obj.soil = None

                else:
                    event_obj.soil_event_type = event.get('soil_event_type')
                    # add soil to event or change it
                    if not event_obj.soil or (event.get('soil') and event['soil'].get('id') != event_obj.soil.id):
                        event_obj.soil = get_or_create_soil(event['soil'], counts)

                # changes to images attached to the event
                # deleted images
                url_originals_saved = [image.get('url_original') for image in event.get('images')] if event.get(
                        'images') else []
                for image_obj in event_obj.images:
                    if image_obj.relative_path not in url_originals_saved:
                        # don't delete image object, but only the association (image might be assigned to other events)
                        get_sql_session().delete([link for link in event_obj.image_to_event_associations if
                                                  link.image.relative_path == image_obj.relative_path][0])

                # newly assigned images
                if event.get('images'):
                    for image in event.get('images'):
                        image_obj = get_sql_session().query(Image).filter(Image.relative_path == image.get(
                                'url_original')).first()

                        # not assigned to any event, yet
                        if not image_obj:
                            image_obj = Image(relative_path=image.get('url_original'))
                            new_list.append(image_obj)

                        # not assigned to that specific event, yet
                        if image_obj not in event_obj.images:
                            event_obj.images.append(image_obj)

        if new_list:
            get_sql_session().add_all(new_list)
        get_sql_session().commit()

        logger.info(' Saving Events: ' + (description := ', '.join([f'{key}: {counts[key]}' for key in counts.keys()])))
        return {'resource': 'EventResource',
                'message': get_message(f'Updated events in database.',
                                       description=description)
                }, 200  # required for closing busy dialog when saving

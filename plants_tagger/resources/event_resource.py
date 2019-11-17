from flask_restful import Resource
import logging
from flask import request
from collections import defaultdict

from flask_2_ui5_py import get_message, throw_exception, MessageType
from sqlalchemy.exc import InvalidRequestError

from plants_tagger import config
from plants_tagger.models import get_sql_session
from plants_tagger.models.files import _util_get_generated_filename, get_thumbnail_relative_path_for_relative_path
from plants_tagger.models.orm_tables import Event, Plant, Pot, object_as_dict, Observation, Image
from plants_tagger.models.update_events import get_or_create_soil
# from plants_tagger.util.json_helper import throw_exception, MessageType

logger = logging.getLogger(__name__)


class EventResource(Resource):
    @staticmethod
    def get(plant_name):
        """returns events from event database table"""

        if not plant_name:
            throw_exception('Plant name required for GET requests')
        # get events which have references to observations, pots, and soils
        results = []
        events_obj = get_sql_session().query(Event).filter(Event.plant_name == plant_name).all()

        event_obj: Event
        for event_obj in events_obj:
            event = object_as_dict(event_obj)

            # read segments from their respective linked tables
            if event_obj.observation:
                event['observation'] = object_as_dict(event_obj.observation)
                if 'height' in event['observation'] and event['observation']['height']:
                    event['observation']['height'] = event['observation']['height'] / 10  # mm to cm
                if 'stem_max_diameter' in event['observation'] and event['observation']['stem_max_diameter']:
                    event['observation']['stem_max_diameter'] = event['observation']['stem_max_diameter'] / 10

            if event_obj.pot:
                event['pot'] = object_as_dict(event_obj.pot)
                if 'diameter_width' in event['pot'] and event['pot']['diameter_width']:
                    event['pot']['diameter_width'] = event['pot']['diameter_width'] / 10

            if event_obj.soil:
                event['soil'] = object_as_dict(event_obj.soil)

                if event_obj.soil.soil_to_component_associations:  # components:

                    event['soil']['components'] = [{'component_name': association.soil_component.component_name,
                                                    'portion':        association.portion} for association
                                                   in event_obj.soil.soil_to_component_associations]

            if event_obj.images:
                event['images'] = []
                for image_obj in event_obj.images:
                    path_small = get_thumbnail_relative_path_for_relative_path(image_obj.relative_path,
                                                                               size=config.size_thumbnail_image)
                    event['images'].append({'id': image_obj.id,
                                            'url_small': path_small,
                                            'url_original': image_obj.relative_path})

            results.append(event)

        logger.info(f'Returning {len(results)} events for {plant_name}.')
        return {'events':  results,
                'message':  get_message(f'Returning {len(results)} events for {plant_name}.',
                                        message_type=MessageType.DEBUG)}

    @staticmethod
    def post():
        """save n events for n plants in database;
        note: there's currently no implementation for modifying an event (neither is on frontend), only for adding
        and deleting"""
        # frontend submits a dict with events for those plants where at least one event has been changed, added, or
        # deleted. it does, however, always submit all these plants' events
        plants_events_dict = request.get_json()['ModifiedEventsDict']
        if not plants_events_dict:
            throw_exception('No plants and events supplied to save.')

        # loop at the plants and their events
        counts = defaultdict(int)
        new_list = []
        for plant_name, events in plants_events_dict.items():

            plant_obj: Plant = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name).first()
            if not plant_obj:
                throw_exception(f'Plant not found: {plant_name}')
            logger.info(f'Plant {plant_obj.plant_name} has {len(plant_obj.events)} events in db:'
                        f' {[e.id for e in plant_obj.events]}')

            # event might have no id in browser but already in backend from earlier save
            # so try to get eventid  from plant name and date (pseudo-key) to avoid events being deleted
            # note: if we "replace" an event in the browser  (i.e. for a specific date, we delete an event and
            # create a new one, then that event in database will be modified, not deleted and re-created
            for event in [e for e in events if not e.get('id')]:
                event_obj_id = get_sql_session().query(Event.id).filter(Event.plant_name == plant_name,
                                                                        Event.date == event.get('date')).scalar()
                if event_obj_id is not None:
                    event['id'] = event_obj_id
                    logger.info(f"Identified event without id from browser as id {event['id']}")
            events_ids = [e.get('id') for e in events]
            logger.info(f'Updating {len(events)} events ({events_ids})for plant {plant_name}')

            # loop at the current plant's database events to find deleted ones
            event_obj: Event
            for event_obj in plant_obj.events:
                if event_obj.id not in events_ids:
                    logger.info(f'Deleting event {event_obj.id}')
                    for link in event_obj.image_to_event_associations:
                        get_sql_session().delete(link)
                    get_sql_session().delete(event_obj)
                    counts['Deleted Events'] += 1

            # loop at the current plant's events from frontend to find new events and modify existing ones
            for event in events:

                # new events (note: only add and delete are implemented)
                if not event.get('id'):
                    # create event record
                    logger.info('Creating event.')
                    event_obj = Event(date=event.get('date'),
                                      event_notes=event.get('event_notes'),
                                      plant=plant_obj
                                      )
                    get_sql_session().add(event_obj)
                    counts['Added Events'] += 1
                else:
                    try:
                        logger.info(f'Getting event  {event.get("id")}.')
                        event_obj = get_sql_session().query(Event).filter(Event.id == event.get('id')).first()
                        if not event_obj:
                            logger.warning(f'Event not found: {event.get("id")}')
                            continue

                    except InvalidRequestError as e:
                        get_sql_session().rollback()
                        logger.error('Serious error occured at event resource (POST). Rollback. See log.',
                                     stack_info=True, exc_info=e)
                        throw_exception('Serious error occured at event resource (POST). Rollback. See log.')

                # create segment records if supplied (otherwise they were not checked in frontend)
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

                if 'pot' in event and not event_obj.pot:
                    pot_obj = Pot()
                    get_sql_session().add(pot_obj)
                    event_obj.pot = pot_obj
                    counts['Added Pots'] += 1
                elif 'pot' not in event and event_obj.pot:
                    # event to pot is n:1 so we don't delete the pot object but only the assignment
                    # get_sql_session().delete(event_obj.pot)
                    event_obj.pot = None
                if 'pot' in event and event_obj.pot:
                    event_obj.pot_event_type = event.get('pot_event_type')
                    event_obj.pot.material = event['pot'].get('material')
                    event_obj.pot.shape_side = event['pot'].get('shape_side')
                    event_obj.pot.shape_top = event['pot'].get('shape_top')
                    event_obj.pot.diameter_width = event['pot'].get('diameter_width') * 10 if event['pot'].get(
                            'diameter_width') else None

                if 'soil' in event and not event_obj.soil:
                    event_obj.soil_event_type = event.get('soil_event_type')
                    # added in util method, but not commited there
                    event_obj.soil = get_or_create_soil(event['soil'], counts)
                elif 'soil' not in event and event_obj.soil:
                    # event to soil is n:1 so we don't delete the soil object but only the assignment
                    event_obj.soil = None

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

        description = ', '.join([f'{key}: {counts[key]}' for key in counts.keys()])
        logger.info(' Saving Events: ' + description)
        return {'resource': 'EventResource',
                'message': get_message(f'Updated events in database.',
                                       description=description)
                }, 200  # required for closing busy dialog when saving

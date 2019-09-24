from flask_restful import Resource
import logging
from flask import request
from collections import defaultdict

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Event, Plant, Pot, object_as_dict, Observation
from plants_tagger.models.update_events import get_or_create_soil
from plants_tagger.util.json_helper import throw_exception, get_message, MessageType

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

            # loop at the current plant's database events to find deleted ones
            event_obj: Event
            for event_obj in plant_obj.events:
                if event_obj.id not in [e.get('id') for e in events]:
                    get_sql_session().delete(event_obj)
                    counts['Deleted Events'] += 1

            # loop at the current plant's events from frontend to find new events
            for event in events:

                # new events (note: only add and delete are implemented)
                if not event.get('id'):

                    # create event record
                    logger.info('Creating event.')
                    event_obj = Event(date=event.get('date'),
                                      event_notes=event.get('event_notes'),
                                      plant=plant_obj
                                      )
                    new_list.append(event_obj)
                    counts['Added Events'] += 1

                    # create segment records if supplied (otherwise they were not checked in frontend)
                    if 'observation' in event:
                        observation_obj = Observation(diseases=event['observation'].get('diseases'),
                                                      observation_notes=event['observation'].get('observation_notes')
                                                      )
                        if event['observation'].get('height'):
                            observation_obj.height = event['observation'].get('height') * 10  # cm to mm
                        if event['observation'].get('stem_max_diameter'):
                            observation_obj.stem_max_diameter = event['observation'].get('stem_max_diameter') * 10

                        event_obj.observation = observation_obj
                        new_list.append(observation_obj)
                        counts['Added Observations'] += 1

                    if 'pot' in event:
                        event_obj.pot_event_type = event.get('pot_event_type')

                        pot_obj = Pot(material=event['pot'].get('material'),
                                      shape_side=event['pot'].get('shape_side'),
                                      shape_top=event['pot'].get('shape_top')
                                      )
                        if event['pot'].get('diameter_width'):
                            pot_obj.diameter_width = event['pot'].get('diameter_width')*10
                        event_obj.pot = pot_obj
                        new_list.append(pot_obj)
                        counts['Added Pots'] += 1

                    if 'soil' in event:
                        # added in util method, but not commited, yet
                        event_obj.soil_event_type = event.get('soil_event_type')
                        event_obj.soil = get_or_create_soil(event['soil'], counts)

        if new_list:
            get_sql_session().add_all(new_list)
        get_sql_session().commit()

        description = ', '.join([f'{key}: {counts[key]}' for key in counts.keys()])
        logger.info(' Saving Events: ' + description)
        return {'resource': 'EventResource',
                'message': get_message(f'Updated events in database.',
                                       description=description)
                }, 200  # required for closing busy dialog when saving

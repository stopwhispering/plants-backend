from flask_restful import Resource, fields, marshal
import logging
from flask import request

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Botany
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)


class SpeciesResource(Resource):
    @staticmethod
    def get():
        species_objects = get_sql_session().query(Botany).all()
        if species_objects:

            resource_fields = {
                'species':      fields.String,
                'description':  fields.String,
                'subgenus':     fields.String,
                'genus':        fields.String,
                'subfamilia':   fields.String,
                'familia':      fields.String,
                'ordo':         fields.String,
                'subclassis':   fields.String,
                'classis':      fields.String,
                'divisio':      fields.String,
                'superdivisio': fields.String,
                'subregnum':    fields.String,
                'notes':        fields.String
                }

            species_collection = marshal(species_objects, resource_fields)
            logger.info(f'Returning {len(species_objects)} species information.')

            return {'SpeciesCollection': species_collection,
                    'message':  {
                        'type':           'Information',
                        'message':        f'Returning species information.',
                        'additionalText': None,
                        'description':    f'Resource: {parse_resource_from_request(request)}\n'
                                          f'Count: {len(species_objects)}'
                        }
                    }, 200

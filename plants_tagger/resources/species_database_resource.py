from json import JSONDecodeError

from flask_restful import Resource
import logging
import pykew.ipni as ipni
import pykew.powo as powo
from flask import request
import json

from plants_tagger.constants import SOURCE_PLANTS, SOURCE_KEW
from plants_tagger.exceptions import TooManyResultsError
from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Taxon, Plant
from plants_tagger.models.taxon import copy_taxon_from_kew, get_distribution_concat, get_synonyms_concat, \
    get_taxa_from_local_database, get_taxa_from_kew_databases
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)


class SpeciesDatabaseResource(Resource):
    @staticmethod
    def get():
        # todo: catch timeout error
        include_kew: bool = json.loads(request.args['includeKew'])
        search_for_genus: bool = json.loads(request.args['searchForGenus'])
        requested_name = request.args['species'].strip()
        if not requested_name:
            return {'error': 'No search name supplied.'}, 500

        # search for supplied species in local database
        results = get_taxa_from_local_database(requested_name+'%', search_for_genus)

        # optionally search in kew's plants of the world database (powo, online via api)
        if include_kew:
            try:
                kew_results = get_taxa_from_kew_databases(requested_name+'*', results, search_for_genus)
                results.extend(kew_results)
            except TooManyResultsError as e:
                return {'error': e.args[0]}, 500
            except JSONDecodeError as e:
                msg = 'ipni.search method raised an Exception.'
                logger.error(msg, exc_info=e)
                return {'error': msg}, 500

        if not results:
            logger.info(f'No search result for search term "{requested_name}".')
            return {'error': f'No search result for search term "{requested_name}".'}, 500

        return {'ResultsCollection': results,
                'message': {
                    'type': 'Information',
                    'message': 'Received species search results',
                    'additionalText': f'Search term "{requested_name}"',
                    'description': f'Count: {len(results)}\nResource: {parse_resource_from_request(request)}'
                    }}, 200

    @staticmethod
    def post():
        """assign the taxon selected on frontend to the plant; the taxon may either already exist in database or we
        need to create it and retrieve the required information from the kew databases"""
        # parse arguments
        fq_id = request.form.get('fqId')
        has_custom_name = json.loads(request.form.get('hasCustomName'))  # plant has an addon not found in kew db
        name_incl_addition = request.form.get('nameInclAddition').strip()  # name incl. custom addition
        source = request.form.get('source')  # either kew database or plants database
        plants_taxon_id = request.form.get('id')  # None if source is kew database, otherwise database
        plant = request.form.get('plant')
        taxon = None

        # easy case: taxon is already in database and no custom taxon is to be created
        if source == SOURCE_PLANTS and not has_custom_name:
            taxon = get_sql_session().query(Taxon).filter(Taxon.id == plants_taxon_id).first()
            if not taxon:
                logger.error(f"Can't find {plants_taxon_id} / {name_incl_addition} in database.")
                return {'error': f"Can't find {plants_taxon_id} / {name_incl_addition} in database."}, 500

        # taxon is already in database, but the user entered a custom name
        # that custom name might already exist in database as well
        elif source == SOURCE_PLANTS and has_custom_name:
            taxon = get_sql_session().query(Taxon).filter(Taxon.name == name_incl_addition,
                                                          Taxon.is_custom).first()
            if taxon:
                logger.info(f'Found custom name in database: {name_incl_addition}')

        # remaining cases: no database record, yet; we need to create it
        if not taxon:
            taxon = copy_taxon_from_kew(fq_id,
                                        has_custom_name,
                                        name_incl_addition)

        # finally, assign the taxon to the plant
        plant_obj: Plant = get_sql_session().query(Plant).filter(Plant.plant_name == plant).first()
        if not plant_obj:
            return {'error': f"Can't find plant {plant}."}, 500

        plant_obj.taxon = taxon
        get_sql_session().commit()

        msg = f'Assigned botanical name "{taxon.name}" to plant "{plant}".'
        return {'toast': msg,
                'botanical_name': taxon.name,
                'message':           {
                    'type':           'Information',
                    'message':        msg,
                    'additionalText': None,
                    'description':    f'Resource: {parse_resource_from_request(request)}'
                    }}, 200



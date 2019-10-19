from json import JSONDecodeError
from flask_restful import Resource
import logging
from flask import request
import json

from plants_tagger.constants import SOURCE_PLANTS
from plants_tagger.exceptions import TooManyResultsError
from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Taxon, object_as_dict
from plants_tagger.models.taxon import copy_taxon_from_kew, get_taxa_from_local_database, get_taxa_from_kew_databases
from plants_tagger.models.taxon_id_mapper import get_gbif_id_from_ipni_id
from flask_2_ui5_py import throw_exception, get_message

logger = logging.getLogger(__name__)


class TaxonToPlantAssignmentsResource(Resource):
    @staticmethod
    def get():
        include_kew: bool = json.loads(request.args['includeKew'])
        search_for_genus: bool = json.loads(request.args['searchForGenus'])
        requested_name = request.args['species'].strip()
        if not requested_name:
            throw_exception('No search name supplied.')

        # search for supplied species in local database
        results = get_taxa_from_local_database(requested_name+'%', search_for_genus)

        # optionally search in kew's plants of the world database (powo, online via api)
        if include_kew:
            try:
                kew_results = get_taxa_from_kew_databases(requested_name+'*', results, search_for_genus)
                results.extend(kew_results)
            except TooManyResultsError as e:
                logger.error('Exception catched.', exc_info=e)
                throw_exception(e.args[0])
            except JSONDecodeError as e:
                logger.error('ipni.search method raised an Exception.', exc_info=e)
                throw_exception('ipni.search method raised an Exception.')

        if not results:
            logger.info(f'No search result for search term "{requested_name}".')
            throw_exception(f'No search result for search term "{requested_name}".')

        return {'ResultsCollection': results,
                'message': get_message('Received species search results',
                                       additional_text=f'Search term "{requested_name}"',
                                       description=f'Count: {len(results)}')
                }, 200

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
                throw_exception(f"Can't find {plants_taxon_id} / {name_incl_addition} in database.")

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

        # The (meta-)database Global Biodiversity Information Facility (gbif) has distribution information,
        # a well-documented API and contains entries from dozens of databases; get an id for it and save it, too
        if taxon.fq_id:
            gbif_id = get_gbif_id_from_ipni_id(taxon.fq_id)
            if gbif_id:
                taxon.gbif_id = gbif_id
                get_sql_session().commit()

        # we will return the taxon's data to be directly added to the model in the frontend
        # only upon saving in the frontend, the assignment is persisted
        # the data returned should be the same as in TaxonResource's get method (which returns all the taxa)
        taxon_dict = object_as_dict(taxon)
        taxon_dict['ipni_id_short'] = taxon_dict['fq_id'][24:]

        message = f'Assigned botanical name "{taxon.name}" to plant "{plant}".'
        logger.info(message)
        return {'taxon_data': taxon_dict,
                'toast': message,
                'botanical_name': taxon.name,
                'message': get_message(message)
                }, 200

from flask_restful import Resource, fields, marshal
import logging
import pykew.ipni as ipni
import pykew.powo as powo
from flask import request
import json

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Botany, Botany2
from plants_tagger.models.taxon import copy_taxon_from_kew, get_distribution_concat, get_synonyms_concat
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)

SOURCE_PLANTS = 'plants database'
SOURCE_KEW = 'kew database'


class SpeciesDatabaseResource(Resource):
    @staticmethod
    def get():
        # todo: catch timeout error
        requested_name = request.args['species'].strip()
        if not requested_name:
            return {'error': 'No search name supplied.'}, 500

        # if exactly that name is already in database, just return this item
        query_all = get_sql_session().query(Botany2).filter(Botany2.name.like(requested_name+'%')).all()
        results = []
        if query_all:
            for query in query_all:
                result = {'source':         SOURCE_PLANTS,
                          'id':                  query.id,
                          'is_custom':           query.is_custom,
                          'authors':             query.authors,
                          'family':              query.family,
                          'name':                query.name,
                          'fqId':                query.fq_id,
                          'genus':               query.genus,
                          'species':             query.species,
                          'namePublishedInYear': query.name_published_in_year,
                          'phylum':              query.phylum,
                          'synonyms_concat':     query.synonyms_concat,
                          'distribution_concat': query.distribution_concat
                          }
                results.append(result)
            logger.info(f'Found query term in plants taxon database.')
        else:

            # search for term on ipni (ipni has more results than powo)
            ipni_search = ipni.search(requested_name)
            if ipni_search.size() > 10:
                return {'error': f'Too many search results for search term "{requested_name}".'}, 500
            elif ipni_search.size() == 0:
                logger.info(f'No search result for search term "{requested_name}".')
                return {'error': f'No search result for search term "{requested_name}".'}, 500

            results = []
            for item in ipni_search:

                result = {'source': SOURCE_KEW,
                          'id': None,
                          'is_custom': False,
                          'authors': item.get('authors'),
                          'family': item.get('family'),
                          'name': item.get('name'),
                          'fqId': item.get('fqId'),
                          'genus': item.get('genus'),
                          'species': item.get('species'),
                          'namePublishedInYear': item.get('publicationYear')
                          }

                powo_lookup = powo.lookup(item.get('fqId'), include=['distribution'])
                if 'error' in powo_lookup:
                    logger.warning(f'No kew powo result for fqId {item.get("fqId")}')
                else:
                    result['phylum'] = powo_lookup.get('phylum')
                    result['author'] = powo_lookup.get('authors')  # overwrite as powo author has more information
                    result['synonyms_concat'] = get_synonyms_concat(powo_lookup)

                    result['distribution_concat'] = get_distribution_concat(powo_lookup)

                results.append(result)
            logger.info(f'Found {len(results)} results from powo search for search term "{requested_name}".')

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
        # table id

        # taxon already in database, no custom name
        if source == SOURCE_PLANTS and not has_custom_name:
            taxon = get_sql_session().query(Botany2).filter(Botany2.id == plants_taxon_id).first()
            if not taxon:
                logger.error(f"Can't find {plants_taxon_id} / {name_incl_addition} in database.")
                return {'error': f"Can't find {plants_taxon_id} / {name_incl_addition} in database."}, 500

        # selected taxon is in database, but we don't know, yet, if selected custom name already exists
        elif source == SOURCE_PLANTS and has_custom_name:
            taxon = get_sql_session().query(Botany2).filter(Botany2.name == name_incl_addition,
                                                            Botany2.is_custom).first()
            if taxon:
                logger.info(f'Found custom name in database: {name_incl_addition}')

        # no database record, yet; thus, we need to create it
        if not taxon:
            taxon = copy_taxon_from_kew(fq_id,
                                        has_custom_name,
                                        name_incl_addition)

        a = 1
        # todo: assign to plant




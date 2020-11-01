from json.decoder import JSONDecodeError
from flask_restful import Resource
import logging
from flask import request

from flask_2_ui5_py import throw_exception, get_message
from pydantic import ValidationError

from plants_tagger.constants import SOURCE_PLANTS
from plants_tagger.exceptions import TooManyResultsError
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.taxon_models import Taxon
from plants_tagger.validation.taxon_validation import PTaxonInfoRequest, PResultsTaxonInfoRequest, \
    PSaveTaxonRequest, PResultsSaveTaxonRequest
from plants_tagger.services.query_taxa import copy_taxon_from_kew, get_taxa_from_local_database, \
    get_taxa_from_kew_databases
from plants_tagger.services.scrape_taxon_id import get_gbif_id_from_ipni_id

logger = logging.getLogger(__name__)


class TaxonSearchDatabaseResource(Resource):
    @staticmethod
    def get():
        # evaluate arguments
        args = None
        try:
            args = PTaxonInfoRequest(**request.args)
            args.species = args.species.strip()
        except ValidationError as err:
            throw_exception(str(err))

        # search for supplied species in local database
        results = get_taxa_from_local_database(plant_name_pattern=f'%{args.species}%',
                                               search_for_genus=args.searchForGenus)

        # optionally search in kew's plants of the world database (powo, online via api)
        if args.includeKew:
            try:
                kew_results = get_taxa_from_kew_databases(args.species + '*', results, args.searchForGenus)
                results.extend(kew_results)
            except TooManyResultsError as e:
                logger.error('Exception catched.', exc_info=e)
                throw_exception(e.args[0])
            except JSONDecodeError as e:
                logger.error('ipni.search method raised an Exception.', exc_info=e)
                throw_exception('ipni.search method raised an Exception.')

        if not results:
            logger.info(f'No search result for search term "{args.species}".')
            throw_exception(f'No search result for search term "{args.species}".')

        results = {'action':            'Get Taxa',
                   'resource':          'TaxonSearchDatabaseResource',
                   'ResultsCollection': results,
                   'message':           get_message('Received species search results',
                                                    additional_text=f'Search term "{args.species}"',
                                                    description=f'Count: {len(results)}')}

        # evaluate output
        try:
            PResultsTaxonInfoRequest(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def post():
        """assign the taxon selected on frontend to the plant; the taxon may either already exist in database or we
        need to create it and retrieve the required information from the kew databases
        Note: The actual assignment is persisted to the database when the plant is saved"""
        # evaluate & parse arguments
        args = None
        try:
            args = PSaveTaxonRequest(**request.form)
            args.nameInclAddition = args.nameInclAddition.strip()
        except ValidationError as err:
            throw_exception(str(err))

        plants_taxon_id = args.id  # None if source is kew database, otherwise database
        taxon = None

        # easy case: taxon is already in database and no custom taxon is to be created
        if args.source == SOURCE_PLANTS and not args.hasCustomName:
            taxon = get_sql_session().query(Taxon).filter(Taxon.id == plants_taxon_id).first()
            if not taxon:
                logger.error(f"Can't find {plants_taxon_id} / {args.nameInclAddition} in database.")
                throw_exception(f"Can't find {plants_taxon_id} / {args.nameInclAddition} in database.")

        # taxon is already in database, but the user entered a custom name
        # that custom name might already exist in database as well
        elif args.source == SOURCE_PLANTS and args.hasCustomName:
            taxon = get_sql_session().query(Taxon).filter(Taxon.name == args.nameInclAddition,
                                                          Taxon.is_custom).first()
            if taxon:
                logger.info(f'Found custom name in database: {args.nameInclAddition}')

        # remaining cases: no database record, yet; we need to create it
        if not taxon:
            taxon = copy_taxon_from_kew(args.fqId,
                                        args.hasCustomName,
                                        args.nameInclAddition)

        # The (meta-)database Global Biodiversity Information Facility (gbif) has distribution information,
        # a well-documented API and contains entries from dozens of databases; get an id for it and save it, too
        # todo: use that data... especially distribution information is far better than what is curr. used
        if taxon.fq_id:
            gbif_id = get_gbif_id_from_ipni_id(taxon.fq_id)
            if gbif_id:
                taxon.gbif_id = gbif_id
                get_sql_session().commit()

        # we will return the taxon's data to be directly added to the model in the frontend
        # only upon saving in the frontend, the assignment is persisted
        # the data returned should be the same as in TaxonResource's get method (which returns all the taxa)
        taxon_dict = taxon.as_dict()
        taxon_dict['ipni_id_short'] = taxon_dict['fq_id'][24:]

        message = f'Assigned botanical name "{taxon.name}" to plant "{args.plant}".'
        logger.info(message)

        results = {'action':         'Save Taxon',
                   'resource':       'TaxonSearchDatabaseResource',
                   'message':        get_message(message),
                   'botanical_name': taxon.name,
                   'taxon_data':     taxon_dict}

        # evaluate output
        try:
            PResultsSaveTaxonRequest(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

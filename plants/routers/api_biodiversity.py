from json.decoder import JSONDecodeError
from threading import Thread
from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session
from starlette.requests import Request

from plants.util.ui_utils import throw_exception, get_message
from plants.constants import SOURCE_PLANTS
from plants.dependencies import get_db
from plants.exceptions import TooManyResultsError
from plants.services.taxon_occurence_image_services import TaxonOccurencesLoader
from plants.validation.taxon_validation import (PTaxonInfoRequest, PResultsTaxonInfoRequest,
                                                PAssignTaxonRequest, PResultsSaveTaxonRequest, PFetchTaxonImages,
                                                PResultsFetchTaxonImages)
from plants.services.query_taxa import (copy_taxon_from_kew, get_taxa_from_local_database,
                                        get_taxa_from_kew_databases)
from plants.services.scrape_taxon_id import get_gbif_id_from_wikidata, gbif_id_from_gbif_api
from plants.models.taxon_models import Taxon

logger = logging.getLogger(__name__)

router = APIRouter(
        # prefix="/taxa",
        tags=["external_biodiversity_databases"],
        responses={404: {"description": "Not found"}},
        )


@router.post("/search_external_biodiversity", response_model=PResultsTaxonInfoRequest)
async def search_external_biodiversity_databases(
        request: Request,
        args: PTaxonInfoRequest,
        db: Session = Depends(get_db)):
    """
    searches taxon pattern in local database and in kew databases (powo and ipni)
    """

    # search for supplied species in local database
    results = get_taxa_from_local_database(plant_name_pattern=f'%{args.species}%',
                                           search_for_genus=args.searchForGenus,
                                           db=db)

    # optionally search in kew's plants of the world database (powo, online via api)
    if args.includeKew:
        try:
            kew_results = get_taxa_from_kew_databases(args.species + '*', results, args.searchForGenus)
            # todo merge not required???
            results.extend(kew_results)
        except TooManyResultsError as e:
            logger.error('Exception catched.', exc_info=e)
            throw_exception(e.args[0], request=request)
        except JSONDecodeError as e:
            logger.error('ipni.search method raised an Exception.', exc_info=e)
            throw_exception('ipni.search method raised an Exception.', request=request)

    if not results:
        logger.info(f'No search result for search term "{args.species}".')
        throw_exception(f'No search result for search term "{args.species}".', request=request)

    results = {'action':            'Get Taxa',
               'resource':          'TaxonSearchDatabaseResource',
               'ResultsCollection': results,
               'message':           get_message('Received species search results',
                                                additional_text=f'Search term "{args.species}"',
                                                description=f'Count: {len(results)}')}

    return results


@router.post("/download_taxon_details", response_model=PResultsSaveTaxonRequest)
async def download_taxon_details(
        request: Request,
        args: PAssignTaxonRequest,
        db: Session = Depends(get_db)):
    """retrieve taxon details from kew databases (sync.) and occurrence images from gbif (async. in thread)
    Note: The actual assignment is persisted to the database when the plant is saved"""

    plants_taxon_id = args.id  # None if source is kew database, otherwise database
    taxon = None

    # easy case: taxon is already in database and no custom taxon is to be created
    if args.source == SOURCE_PLANTS and not args.hasCustomName:
        taxon = db.query(Taxon).filter(Taxon.id == plants_taxon_id).first()
        if not taxon:
            logger.error(f"Can't find {plants_taxon_id} / {args.nameInclAddition} in database.")
            throw_exception(f"Can't find {plants_taxon_id} / {args.nameInclAddition} in database.", request=request)

    # taxon is already in database, but the user entered a custom name
    # that custom name might already exist in database as well
    elif args.source == SOURCE_PLANTS and args.hasCustomName:
        taxon = db.query(Taxon).filter(Taxon.name == args.nameInclAddition,
                                       Taxon.is_custom).first()
        if taxon:
            logger.info(f'Found custom name in database: {args.nameInclAddition}')

    # remaining cases: no database record, yet; we need to create it
    if not taxon:
        taxon = copy_taxon_from_kew(args.fqId,
                                    args.hasCustomName,
                                    args.nameInclAddition,
                                    db)

    # The (meta-)database Global Biodiversity Information Facility (gbif) has distribution information,
    # a well-documented API and contains entries from dozens of databases; get an id for it and save it, too
    # todo: use that data... especially distribution information is far better than what is curr. used
    if taxon.fq_id:
        gbif_id = gbif_id_from_gbif_api(taxon.name, taxon.fq_id) or get_gbif_id_from_wikidata(taxon.fq_id)
        if gbif_id:
            taxon.gbif_id = gbif_id
            db.commit()

            # lookup ocurrences & images at gbif and generate thumbnails
            loader = TaxonOccurencesLoader()
            thread = Thread(target=loader.scrape_occurrences_for_taxon, args=(gbif_id, db))
            logger.info(f'Starting thread to load occurences for gbif_id {gbif_id}')
            thread.start()

    # we will return the taxon's data to be directly added to the model in the frontend
    # only upon saving in the frontend, the assignment is persisted
    # the data returned should be the same as in TaxonResource's get method (which returns all the taxa)
    taxon_dict = taxon.as_dict()
    taxon_dict['ipni_id_short'] = taxon_dict['fq_id'][24:]

    message = f'Assigned botanical name "{taxon.name}" to plant id {args.plant_id}.'
    logger.info(message)

    results = {'action':         'Save Taxon',
               'resource':       'TaxonSearchDatabaseResource',
               'message':        get_message(message),
               'botanical_name': taxon.name,
               'taxon_data':     taxon_dict}

    return results


@router.post("/fetch_taxon_images", response_model=PResultsFetchTaxonImages)
async def fetch_taxon_images(
        request: Request,
        args: PFetchTaxonImages,
        db: Session = Depends(get_db)):
    """(re)fetch taxon images from gbif and create thumbnails"""

    # lookup ocurrences & images at gbif and generate thumbnails
    loader = TaxonOccurencesLoader()
    loader.scrape_occurrences_for_taxon(gbif_id=args.gbif_id, db=db)

    taxon = db.query(Taxon).filter(Taxon.gbif_id == args.gbif_id).first()
    if not taxon:
        # would probably have raised earlier
        logger.error(f"Can't find taxon for GBIF ID {args.gbif_id} in database.")
        throw_exception(f"Can't find taxon for GBIF ID {args.gbif_id} in database.", request=request)
    occurrence_images = [o.as_dict() for o in taxon.occurrence_images]

    message = f'Refetched occurences for GBIF ID {args.gbif_id}'
    logger.info(message)

    results = {'action':         'Save Taxon',
               'resource':       'TaxonSearchDatabaseResource',
               'message':        get_message(message),
               'occurrenceImages':     occurrence_images}

    return results

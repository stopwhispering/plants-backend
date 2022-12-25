from json.decoder import JSONDecodeError
from threading import Thread
from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session
from starlette.requests import Request

from plants.services.taxonomy_lookup_details import TaxonomyLookupDetails
from plants.util.ui_utils import throw_exception, get_message
from plants.dependencies import get_db
from plants.exceptions import TooManyResultsError
from plants.services.taxonomy_occurence_images import TaxonOccurencesLoader
from plants.validation.taxon_validation import (FTaxonInfoRequest, BResultsTaxonInfoRequest,
                                                FAssignTaxonRequest, BResultsSaveTaxonRequest, FFetchTaxonOccurrenceImagesRequest,
                                                BResultsFetchTaxonImages, BSearchResultSource)
from plants.services.taxonomy_search import TaxonomySearch
from plants.services.taxonomy_lookup_gbif_id import GBIFIdentifierLookup
from plants.models.taxon_models import Taxon

logger = logging.getLogger(__name__)

router = APIRouter(
    # prefix="/taxa",
    tags=["external_biodiversity_databases"],
    responses={404: {"description": "Not found"}},
)


@router.post("/search_taxa_by_name", response_model=BResultsTaxonInfoRequest)
async def search_taxa_by_name(
        request: Request,
        taxon_info_request: FTaxonInfoRequest,
        db: Session = Depends(get_db)):
    """
    searches taxon pattern in
        (1) local database and
        (2) in kew databases (powo and ipni) if requested
    """
    taxonomy_search = TaxonomySearch(include_external_apis=taxon_info_request.include_external_apis,
                                     search_for_genus_not_species=taxon_info_request.search_for_genus_not_species,
                                     db=db)
    try:
        results = taxonomy_search.search(taxon_info_request.taxon_name_pattern)
    except TooManyResultsError as e:
        logger.error('Exception catched.', exc_info=e)
        throw_exception(e.args[0], request=request)
    except JSONDecodeError as e:
        logger.error('ipni.search method raised an Exception.', exc_info=e)
        throw_exception('ipni.search method raised an Exception.', request=request)

    if not results:  # noqa
        logger.info(f'No search result for search term "{taxon_info_request.taxon_name_pattern}".')
        throw_exception(f'No search result for search term "{taxon_info_request.taxon_name_pattern}".', request=request)

    results = {'action': 'Search Taxa',
               # 'resource': 'TaxonSearchDatabaseResource',  # todo remove
               'ResultsCollection': results,
               'message': get_message('Received species search results',
                                      additional_text=f'Search term "{taxon_info_request.taxon_name_pattern}"',
                                      description=f'Count: {len(results)}')}

    return results


@router.post("/retrieve_details_for_selected_taxon", response_model=BResultsSaveTaxonRequest)
async def retrieve_details_for_selected_taxon(
        request: Request,
        assign_taxon_request: FAssignTaxonRequest,
        db: Session = Depends(get_db)):
    """
    retrieve taxon details from kew databases "POWO" and "IPNI" (sync.) and occurrence images
    from GBIF (async. in thread after response is sent)
    Note: The actual assignment is persisted to the database when the plant is saved; here, we only
    insert the taxon into the database if it is not already there.
    """
    taxon = None

    # easy case: taxon is already in database and no custom taxon is to be created
    if (assign_taxon_request.source == BSearchResultSource.SOURCE_PLANTS_DB
            and not assign_taxon_request.hasCustomName):
        taxon = db.query(Taxon).filter(Taxon.id == assign_taxon_request.taxon_id).first()
        if not taxon:
            logger.error(f"Can't find {assign_taxon_request.taxon_id} / "
                         f"{assign_taxon_request.nameInclAddition} in database.")
            throw_exception(f"Can't find {assign_taxon_request.taxon_id} / "
                            f"{assign_taxon_request.nameInclAddition} in database.", request=request)

    # taxon is already in database, but the user entered a custom name
    # that custom name might already exist in database as well
    elif (assign_taxon_request.source == BSearchResultSource.SOURCE_PLANTS_DB
          and assign_taxon_request.hasCustomName):
        taxon = db.query(Taxon).filter(Taxon.name == assign_taxon_request.nameInclAddition,
                                       Taxon.is_custom).first()
        if taxon:
            logger.info(f'Found custom name in database: {assign_taxon_request.nameInclAddition}')

    # either taxon data was requested from kew databases or the local db does not contain the taxon
    # retrieve information from Kew databases POWO and IPNI and create new taxon db record
    if not taxon:
        taxonomy_lookup_details = TaxonomyLookupDetails(db=db)
        taxon = taxonomy_lookup_details.lookup(assign_taxon_request.lsid,
                                               assign_taxon_request.hasCustomName,
                                               assign_taxon_request.nameInclAddition)
        taxonomy_lookup_details.save_taxon(taxon)

    # The (meta-)database "Global Biodiversity Information Facility" (GBIF) has distribution information,
    # a well-documented API and contains entries from dozens of databases; get an ID for it and save it, too
    # todo: use that data... especially distribution information is far better than what is curr. used
    if not taxon.is_custom:
        gbif_identifier_lookup = GBIFIdentifierLookup()
        gbif_id = gbif_identifier_lookup.lookup(taxon_name=taxon.name, lsid=taxon.lsid)
        # gbif_id = gbif_id_from_gbif_api(taxon.name, taxon.fq_id) or get_gbif_id_from_wikidata(taxon.fq_id)
        if gbif_id:
            taxon.gbif_id = gbif_id
            db.commit()

            # lookup ocurrences & image URLs at GBIF and generate thumbnails for found image URLs
            loader = TaxonOccurencesLoader(db=db)
            thread = Thread(target=loader.scrape_occurrences_for_taxon, args=gbif_id)
            logger.info(f'Starting thread to load occurences for gbif_id {gbif_id}')
            thread.start()

    # we will return the taxon's data to be directly added to the model in the frontend
    # only upon saving in the frontend, the assignment is persisted
    # the data returned should be the same as in TaxonResource's get method (which returns all the taxa)
    taxon_dict = taxon.as_dict()
    # taxon_dict['ipni_id_short'] = taxon_dict['fq_id'][24:]

    message = f'Assigned botanical name "{taxon.name}" to plant id {assign_taxon_request.plant_id}.'
    logger.info(message)

    results = {'action': 'Save Taxon',
               'resource': 'TaxonSearchDatabaseResource',
               'message': get_message(message),
               'botanical_name': taxon.name,
               'taxon_data': taxon_dict}

    return results


@router.post("/fetch_taxon_occurrence_images", response_model=BResultsFetchTaxonImages)
async def fetch_taxon_occurrence_images(
        request: Request,
        fetch_taxon_occurrence_images_request: FFetchTaxonOccurrenceImagesRequest,
        db: Session = Depends(get_db)):
    """(re)fetch taxon images from gbif and create thumbnails"""

    # lookup ocurrences & images at gbif and generate thumbnails
    loader = TaxonOccurencesLoader(db=db)
    loader.scrape_occurrences_for_taxon(gbif_id=fetch_taxon_occurrence_images_request.gbif_id)

    taxon = db.query(Taxon).filter(Taxon.gbif_id == fetch_taxon_occurrence_images_request.gbif_id).first()
    if not taxon:
        # would probably have raised earlier
        logger.error(f"Can't find taxon for GBIF ID {fetch_taxon_occurrence_images_request.gbif_id} in database.")
        throw_exception(f"Can't find taxon for GBIF ID {fetch_taxon_occurrence_images_request.gbif_id} in database.", request=request)
    occurrence_images = [o.as_dict() for o in taxon.occurrence_images]

    message = f'Refetched occurences for GBIF ID {fetch_taxon_occurrence_images_request.gbif_id}'
    logger.info(message)

    results = {'action': 'Save Taxon',
               'resource': 'TaxonSearchDatabaseResource',
               'message': get_message(message),
               'occurrenceImages': occurrence_images}

    return results

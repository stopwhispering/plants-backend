from json.decoder import JSONDecodeError
from fastapi import APIRouter, Depends
import logging
from starlette.requests import Request

from plants.dependencies import get_taxon_dal
from plants.modules.plant.taxon_dal import TaxonDAL
from plants.shared.message_services import throw_exception, get_message
from plants.exceptions import TooManyResultsError
from plants.modules.biodiversity.taxonomy_occurence_images import TaxonOccurencesLoader
from plants.modules.taxon.schemas import (
    FTaxonInfoRequest, BResultsTaxonInfoRequest, FFetchTaxonOccurrenceImagesRequest,
    BResultsFetchTaxonImages
)
from plants.modules.biodiversity.taxonomy_search import TaxonomySearch

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["external_biodiversity_databases"],
    responses={404: {"description": "Not found"}},
)


@router.post("/search_taxa_by_name", response_model=BResultsTaxonInfoRequest)
async def search_taxa_by_name(
        request: Request,
        taxon_info_request: FTaxonInfoRequest,
        taxon_dal: TaxonDAL = Depends(get_taxon_dal)):
    """
    searches taxon pattern in
        (1) local database and
        (2) in kew databases (powo and ipni) if requested
    """
    taxonomy_search = TaxonomySearch(include_external_apis=taxon_info_request.include_external_apis,
                                     search_for_genus_not_species=taxon_info_request.search_for_genus_not_species,
                                     taxon_dal=taxon_dal)
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
               'ResultsCollection': results,
               'message': get_message('Received species search results',
                                      additional_text=f'Search term "{taxon_info_request.taxon_name_pattern}"',
                                      description=f'Count: {len(results)}')}

    return results


@router.post("/fetch_taxon_occurrence_images", response_model=BResultsFetchTaxonImages)
async def fetch_taxon_occurrence_images(
        fetch_taxon_occurrence_images_request: FFetchTaxonOccurrenceImagesRequest,
        taxon_dal: TaxonDAL = Depends(get_taxon_dal)
):
    """(re)fetch taxon images from gbif and create thumbnails"""

    # lookup ocurrences & images at gbif and generate thumbnails
    loader = TaxonOccurencesLoader(taxon_dal=taxon_dal)
    occurrence_images = loader.scrape_occurrences_for_taxon(gbif_id=fetch_taxon_occurrence_images_request.gbif_id)

    message = f'Refetched occurences for GBIF ID {fetch_taxon_occurrence_images_request.gbif_id}'
    logger.info(message)

    results = {'action': 'Save Taxon',
               'message': get_message(message),
               'occurrence_images': occurrence_images}

    return results

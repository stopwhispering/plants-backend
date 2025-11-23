from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from plants.dependencies import get_taxon_dal
from plants.modules.biodiversity.taxonomy_occurence_images import TaxonOccurencesLoader
from plants.modules.biodiversity.taxonomy_search import (
    FinalSearchResult,
    TaxonomySearch,
)
from plants.modules.taxon.schemas import (
    FetchTaxonOccurrenceImagesRequest,
    FetchTaxonOccurrenceImagesResponse,
    SearchTaxaRequest,
    SearchTaxaResponse,
)

# if TYPE_CHECKING:
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.message_services import get_message, throw_exception

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["external_biodiversity_databases"],
    responses={404: {"description": "Not found"}},
)


@router.post("/search_taxa_by_name", response_model=SearchTaxaResponse)
async def search_taxa_by_name(
    taxon_info_request: SearchTaxaRequest,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
) -> Any:
    """Searches taxon pattern in (1) local database and (2) in kew databases (powo and ipni) if
    requested."""

    # temporary workaround:
    # the powo/ipni servers sometimes block requests with a 403 error when using the official
    # pykew library. Monkey-patch requests.get to use a common User-Agent header "fixes" the
    # problem. As a TEMPORARY workaround this patch is applied only during the execution of this
    # function and restored afterwards. Note to myself: find a better solution later if the
    # problem persists.
    import requests

    original_get = requests.get

    def patched_get(*args, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
        return original_get(*args, headers=headers, **kwargs)

    requests.get = patched_get
    # Now any library using requests.get will get the custom User-Agent

    taxonomy_search = TaxonomySearch(
        include_external_apis=taxon_info_request.include_external_apis,
        search_for_genus_not_species=taxon_info_request.search_for_genus_not_species,
        taxon_dal=taxon_dal,
    )
    search_results: list[FinalSearchResult] = await taxonomy_search.search(
        taxon_info_request.taxon_name_pattern
    )

    requests.get = original_get

    if not search_results:
        throw_exception(
            f"No search result for search term " f'"{taxon_info_request.taxon_name_pattern}".',
        )

    return {
        "action": "Search Taxa",
        "ResultsCollection": search_results,
        "message": get_message(
            "Received species search results",
            description=f"Count: {len(search_results)}",
        ),
    }


@router.post("/fetch_taxon_occurrence_images", response_model=FetchTaxonOccurrenceImagesResponse)
async def fetch_taxon_occurrence_images(
    fetch_taxon_occurrence_images_request: FetchTaxonOccurrenceImagesRequest,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
) -> Any:
    """(re)fetch taxon images from gbif and create thumbnails."""

    # lookup ocurrences & images at gbif and generate thumbnails
    loader = TaxonOccurencesLoader(taxon_dal=taxon_dal)
    occurrence_images = await loader.scrape_occurrences_for_taxon(
        gbif_id=fetch_taxon_occurrence_images_request.gbif_id
    )

    message = (
        f"Refetched occurences for GBIF ID " f"{fetch_taxon_occurrence_images_request.gbif_id}"
    )
    logger.info(message)

    return {
        "action": "Save Taxon",
        "message": get_message(message),
        "occurrence_images": occurrence_images,
    }

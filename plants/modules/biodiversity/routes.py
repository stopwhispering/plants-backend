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
    BResultsFetchTaxonImages,
    BResultsTaxonInfoRequest,
    FFetchTaxonOccurrenceImagesRequest,
    FTaxonInfoRequest,
)

# if TYPE_CHECKING:
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.message_services import get_message, throw_exception

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["external_biodiversity_databases"],
    responses={404: {"description": "Not found"}},
)


@router.post("/search_taxa_by_name", response_model=BResultsTaxonInfoRequest)
async def search_taxa_by_name(
    taxon_info_request: FTaxonInfoRequest,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
) -> Any:
    """Searches taxon pattern in (1) local database and (2) in kew databases (powo and
    ipni) if requested."""
    taxonomy_search = TaxonomySearch(
        include_external_apis=taxon_info_request.include_external_apis,
        search_for_genus_not_species=taxon_info_request.search_for_genus_not_species,
        taxon_dal=taxon_dal,
    )
    search_results: list[FinalSearchResult] = await taxonomy_search.search(
        taxon_info_request.taxon_name_pattern
    )

    if not search_results:  # noqa
        throw_exception(
            f"No search result for search term "
            f'"{taxon_info_request.taxon_name_pattern}".',
        )

    return {
        "action": "Search Taxa",
        "ResultsCollection": search_results,
        "message": get_message(
            "Received species search results",
            additional_text=f'Search term "{taxon_info_request.taxon_name_pattern}"',
            description=f"Count: {len(search_results)}",
        ),
    }


@router.post("/fetch_taxon_occurrence_images", response_model=BResultsFetchTaxonImages)
async def fetch_taxon_occurrence_images(
    fetch_taxon_occurrence_images_request: FFetchTaxonOccurrenceImagesRequest,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
) -> Any:
    """(re)fetch taxon images from gbif and create thumbnails."""

    # lookup ocurrences & images at gbif and generate thumbnails
    loader = TaxonOccurencesLoader(taxon_dal=taxon_dal)
    occurrence_images = loader.scrape_occurrences_for_taxon(
        gbif_id=fetch_taxon_occurrence_images_request.gbif_id
    )

    message = (
        f"Refetched occurences for GBIF ID "
        f"{fetch_taxon_occurrence_images_request.gbif_id}"
    )
    logger.info(message)

    return {
        "action": "Save Taxon",
        "message": get_message(message),
        "occurrence_images": occurrence_images,
    }

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi.concurrency import run_in_threadpool
from pykew import ipni, powo
from pykew.ipni_terms import Filters

from plants import settings
from plants.exceptions import TooManyResultsError
from plants.modules.biodiversity.taxonomy_shared_functions import (
    get_accepted_synonym_label,
    get_concatenated_distribution,
)
from plants.modules.taxon.enums import FBRank
from plants.shared.message_services import throw_exception

if TYPE_CHECKING:
    from plants.modules.biodiversity.api_typedefs import IpniSearchResultTaxonDict
    from plants.modules.taxon.models import Taxon
    from plants.modules.taxon.taxon_dal import TaxonDAL

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class _BaseSearchResult:  # pylint: disable=too-many-instance-attributes
    lsid: str
    name_published_in_year: int | None
    name: str
    rank: str
    family: str
    genus: str
    species: str | None
    infraspecies: str | None
    hybrid: bool
    hybridgenus: bool


@dataclass(kw_only=True)
class _ParsedIpniSearchResult(_BaseSearchResult):
    pass


@dataclass(kw_only=True)
class _ParsedApiSearchResult(_BaseSearchResult):
    """ParsedIpniSearchResult + additional fields from POWO API."""

    basionym: str | None
    taxonomic_status: str
    authors: str
    synonym: bool
    synonyms_concat: str | None
    distribution_concat: str | None


@dataclass(kw_only=True)
class _DBSearchResult(_ParsedApiSearchResult):  # pylint: disable=too-many-instance-attributes
    id: int
    is_custom: bool
    count: int
    count_inactive: int
    custom_suffix: str | None
    custom_rank: FBRank | None
    custom_infraspecies: str | None
    cultivar: str | None
    affinis: str | None


@dataclass(kw_only=True)
class FinalSearchResult(_ParsedApiSearchResult):  # pylint: disable=too-many-instance-attributes
    in_db: bool
    count: int
    count_inactive: int
    id: int | None = None
    custom_suffix: str | None = None
    custom_rank: FBRank | None = None
    custom_infraspecies: str | None = None
    cultivar: str | None = None
    affinis: str | None = None
    is_custom: bool = False


class TaxonomySearch:
    def __init__(
        self,
        *,
        include_external_apis: bool,
        search_for_genus_not_species: bool,
        taxon_dal: TaxonDAL,
    ):
        self.include_external_apis = include_external_apis
        self.search_for_genus_not_species = search_for_genus_not_species
        self.taxon_dal = taxon_dal

    async def search(self, taxon_name_pattern: str) -> list[FinalSearchResult]:
        """Search for a taxon name via pattern, first in local database, then in external APIs merge
        results from local database and external APIs."""
        # search for taxa already in the database
        local_results: list[_DBSearchResult] = await self._query_taxa_in_local_database(
            taxon_name_pattern=f"%{taxon_name_pattern}%",
            search_for_genus_not_species=self.search_for_genus_not_species,
        )
        results: list[FinalSearchResult] = [
            FinalSearchResult(**local_result.__dict__, in_db=True) for local_result in local_results
        ]

        # optionally, search in external biodiversity databases "ipni" and "powo"
        if self.include_external_apis:
            api_searcher = ApiSearcher(
                search_for_genus_not_species=self.search_for_genus_not_species
            )

            kew_results: list[_ParsedApiSearchResult] = await run_in_threadpool(
                api_searcher.search_taxa_in_external_apis,
                plant_name_pattern=taxon_name_pattern,  # no %/* required here
                local_results=local_results,
            )

            results.extend(
                [
                    FinalSearchResult(**kew_result.__dict__, in_db=False, count=0, count_inactive=0)
                    for kew_result in kew_results
                ]
            )
        return results

    @staticmethod
    def _get_search_result_from_db_taxon(taxon: Taxon) -> _DBSearchResult:
        return _DBSearchResult(
            id=taxon.id,
            count=len([p for p in taxon.plants if p.active]),
            count_inactive=len([p for p in taxon.plants if not p.active]),
            is_custom=taxon.is_custom,
            synonym=taxon.synonym,
            authors=taxon.authors,
            family=taxon.family,
            name=taxon.name,
            rank=taxon.rank,
            taxonomic_status=taxon.taxonomic_status,
            lsid=taxon.lsid,
            genus=taxon.genus,
            species=taxon.species,
            infraspecies=taxon.infraspecies,
            hybrid=taxon.hybrid,
            hybridgenus=taxon.hybridgenus,
            custom_suffix=taxon.custom_suffix,
            custom_rank=taxon.custom_rank,
            custom_infraspecies=taxon.custom_infraspecies,
            cultivar=taxon.cultivar,
            affinis=taxon.affinis,
            name_published_in_year=taxon.name_published_in_year,
            basionym=taxon.basionym,
            # 'phylum': taxon.phylum,
            synonyms_concat=taxon.synonyms_concat,
            distribution_concat=taxon.distribution_concat,
        )

    async def _query_taxa_in_local_database(
        self, taxon_name_pattern: str, *, search_for_genus_not_species: bool
    ) -> list[_DBSearchResult]:
        """Searches term in local botany database and returns results in web- format."""
        if search_for_genus_not_species:
            taxa = await self.taxon_dal.get_taxa_by_name_pattern(taxon_name_pattern, FBRank.GENUS)
        else:
            taxa = await self.taxon_dal.get_taxa_by_name_pattern(taxon_name_pattern)

        results = [self._get_search_result_from_db_taxon(taxon) for taxon in taxa]
        logger.info(
            "Found query term in plants taxon database."
            if results
            else "Query term not found in plants taxon database."
        )
        return results


class ApiSearcher:
    def __init__(self, *, search_for_genus_not_species: bool):
        self.search_for_genus_not_species = search_for_genus_not_species

    def search_taxa_in_external_apis(
        self,
        plant_name_pattern: str,
        local_results: list[_DBSearchResult],
    ) -> list[_ParsedApiSearchResult]:
        """Searches term in kew's International Plant Name Index ("IPNI") and Plants of the World
        ("POWO"); ignores entries included in the local_results list."""
        # First step: search in the International Plant Names Index (IPNI) which has
        # slightly more items than POWO
        ipni_results = self._search_taxa_in_ipni_api(
            plant_name_pattern=plant_name_pattern, ignore_local_db_results=local_results
        )

        # Second step: for each IPNI result, search in POWO for more details if
        # available
        api_results: list[_ParsedApiSearchResult] = []
        ipni_result: _ParsedIpniSearchResult
        for ipni_result in ipni_results:
            api_results.append(self._update_taxon_from_powo_api(ipni_result))

        logger.info(
            f"Found {len(api_results)} results from IPNI/POWO search for search term "
            f'"{plant_name_pattern}".'
        )
        return api_results

    def _search_taxa_in_ipni_api(
        self, plant_name_pattern: str, ignore_local_db_results: list[_DBSearchResult]
    ) -> list[_ParsedIpniSearchResult]:
        """Search for species / genus pattern in Kew's IPNI database skip if already in local
        database might raise TooManyResultsError."""
        results: list[_ParsedIpniSearchResult] = []

        if not self.search_for_genus_not_species:
            filters = [Filters.specific, Filters.infraspecific]
        else:
            filters = [Filters.generic, Filters.infrageneric]
        ipni_search = ipni.search(plant_name_pattern, filters=filters)

        if ipni_search.size() > settings.plants.taxon_search_max_results:
            raise TooManyResultsError(plant_name_pattern, ipni_search.size())

        if ipni_search.size() == 0:
            return results

        ipni_result: IpniSearchResultTaxonDict
        for ipni_result in ipni_search:
            # discard results that are not in POWO
            if not ipni_result.get("inPowo"):
                continue

            # check if that item is already included in the local results; if so, skip
            if any(
                r
                for r in ignore_local_db_results
                if not r.is_custom and r.lsid == ipni_result["fqId"]
            ):
                continue

            rank, species, infraspecies = self._parse_infraspecific_rank(ipni_result)

            # build additional results from IPNI data
            result = _ParsedIpniSearchResult(
                # IPNI Life Sciences Identifier (used by POWO and IPNI)
                lsid=ipni_result["fqId"],
                name_published_in_year=ipni_result.get("publicationYear"),
                name=ipni_result["name"],
                rank=rank,
                family=ipni_result["family"],
                genus=ipni_result["genus"],
                species=species,
                infraspecies=infraspecies,
                hybrid=ipni_result["hybrid"],
                hybridgenus=ipni_result["hybridGenus"],
            )
            results.append(result)
        return results

    @staticmethod
    def _parse_infraspecific_rank(
        ipni_result: IpniSearchResultTaxonDict,
    ) -> tuple[str, str | None, str | None]:
        # treat infraspecific taxa
        # a taxon may have 0 or 1 infra-specific name, never multiple
        rank = ipni_result["rank"]
        if rank == "f.":  # in some cases, forma comes as "f."
            rank = FBRank.FORMA.value
        if rank == FBRank.GENUS.value:
            species = None
            infraspecies = None
        elif rank == FBRank.SPECIES.value:
            species = ipni_result["species"]
            infraspecies = None
        elif (
            rank
            in (
                FBRank.SUBSPECIES.value,
                FBRank.VARIETY.value,
                FBRank.FORMA.value,
                FBRank.SUBFORMA.value,
            )
            or rank == "nothovar."
        ):
            species = ipni_result["species"]
            infraspecies = ipni_result["infraspecies"]
        else:
            raise ValueError(f"Unexpected rank {rank} for {ipni_result['fqId']}.")
        return rank, species, infraspecies

    @staticmethod
    def _update_taxon_from_powo_api(
        result: _ParsedIpniSearchResult,
    ) -> _ParsedApiSearchResult:
        """For the supplied search result entry, fetch additional information from "Plants of the
        World" API."""
        # POWO uses LSID as ID just like IPNI
        powo_lookup = powo.lookup(result.lsid, include=["distribution"])
        if "error" in powo_lookup:
            throw_exception(f"No Plants of the World result for LSID {result.lsid}")

        basionym = powo_lookup["basionym"].get("name") if "basionym" in powo_lookup else None

        ext_result = _ParsedApiSearchResult(
            **result.__dict__,
            basionym=basionym,
            taxonomic_status=powo_lookup.get("taxonomicStatus"),
            authors=powo_lookup.get("authors"),
            synonym=powo_lookup.get("synonym"),
            synonyms_concat=get_accepted_synonym_label(powo_lookup),
            distribution_concat=get_concatenated_distribution(powo_lookup),
        )

        if "name_published_in_year" in powo_lookup:
            ext_result.name_published_in_year = powo_lookup["name_published_in_year"]

        return ext_result

from __future__ import annotations

import logging
import re
import requests
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi.concurrency import run_in_threadpool
from pykew import ipni  # , powo
from pykew.ipni_terms import Filters
from pygbif import species as gbif_species
from requests.exceptions import HTTPError

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

    # basionym: str | None
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

            # since local db search and ipni search return different results, we need to check
            # if the result is already in the local db
            for kew_result in kew_results:
                local_search_result = await self._find_local_taxon_if_available(kew_result)
                if local_search_result:
                    results.append(
                        FinalSearchResult(
                            **local_search_result.__dict__,
                            in_db=True
                        )
                    )
                    kew_results.remove(kew_result)

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
            # basionym=taxon.basionym,
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

    async def _find_local_taxon_if_available(self, kew_result: _ParsedApiSearchResult
                                             ) -> _DBSearchResult | None:
        local_taxa = await self.taxon_dal.by_lsid(lsid=kew_result.lsid, include_custom=False)
        if len(local_taxa) > 1:
            raise ValueError(
                f"Found multiple taxa with LSID {kew_result.lsid} in local database. "
                "This should not happen."
            )
        elif not local_taxa:
            return None

        local_taxon = local_taxa[0]
        local_db_results = self._get_search_result_from_db_taxon(local_taxon)
        assert local_db_results, "Expected results to be not empty, but got empty list."

        return local_db_results


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
            gbif_result = self._update_taxon_from_gbif_api(ipni_result)
            if gbif_result:
                api_results.append(gbif_result)

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
    def _fetch_from_gbif(result: _ParsedIpniSearchResult) -> _ParsedApiSearchResult | None:
        """Fetch taxonomic details for the given IPNI result via pygbif.

        Searches the IPNI dataset at GBIF by taxon name, matches on LSID, then
        fetches backbone details, synonyms, and distributions.
        Returns None if the taxon cannot be matched.
        """
        _IPNI_DATASET_KEY = "046bbc50-cae2-47ff-aa43-729fbf53f7c5"

        # Step 1 — resolve LSID → GBIF nubKey via the IPNI dataset at GBIF
        name_lookup = gbif_species.name_lookup(
            q=result.name, datasetKey=_IPNI_DATASET_KEY, limit=20
        )
        matched = next(
            (r for r in name_lookup.get("results", []) if r.get("taxonID") == result.lsid),
            None,
        )
        if not matched:
            return None

        nub_key: int = matched["nubKey"]

        # Step 2 — taxon details from backbone (authors, taxonomic status, synonym flag)
        usage = gbif_species.name_usage(key=nub_key)

        # Try to extract publication year:
        # • IPNI dataset match has authorship like "Schnland, 1910"
        # • backbone usage has publishedIn like "Trans. Roy. Soc. South Africa 1: 391 (1910)"
        # Take the first 4-digit year found in either string.
        _year_src = matched.get("authorship") or usage.get("publishedIn") or ""
        _year_match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", _year_src)
        name_published_in_year: int | None = (
            int(_year_match.group(1)) if _year_match else result.name_published_in_year
        )

        # Step 3 — synonyms list
        syn_names = [
            s.get("scientificName")
            for s in gbif_species.name_usage(key=nub_key, data="synonyms").get("results", [])
        ]

        # Step 4 — distribution records; prefer WCVP source for quality,
        # fall back to any record that carries a TDWG locationId, then all records
        dist_records: list[dict] = gbif_species.name_usage(
            key=nub_key, data="distributions"
        ).get("results", [])
        wcvp_dists = [d for d in dist_records if "WCVP" in d.get("source", "") and 'locality' in d]
        tdwg_dists = [d for d in dist_records if d.get("locationId")]
        src_records = wcvp_dists or tdwg_dists or dist_records

        # Build distribution_concat in the same format as get_concatenated_distribution()
        introduced_statuses = {"INTRODUCED", "MANAGED", "CULTIVATED"}

        def _label(d: dict) -> str | None:
            return d.get("locality") or d.get("locationId") or d.get("country")

        native_labels = [
            _label(d) for d in src_records
            if d.get("establishmentMeans", "").upper() not in introduced_statuses
            and _label(d) is not None
        ]
        intro_labels = [
            _label(d) for d in src_records
            if d.get("establishmentMeans", "").upper() in introduced_statuses
            and _label(d) is not None
        ]
        dist_parts: list[str] = []
        if native_labels:
            dist_parts.append(", ".join(native_labels) + " (natives)")
        if intro_labels:
            dist_parts.append(", ".join(intro_labels) + " (introduced)")
        distribution_concat: str | None = ", ".join(dist_parts) if dist_parts else None

        # Build synonyms_concat: synonym taxon → "Accepted: <name>",
        # accepted taxon → joined list of its synonyms
        if usage.get("synonym"):
            accepted_name = usage.get("accepted") or usage.get("species")
            synonyms_concat: str | None = (
                f"Accepted: {accepted_name}" if accepted_name else None
            )
        else:
            synonyms_concat = ", ".join(syn_names) if syn_names else None

        return _ParsedApiSearchResult(
            **{**result.__dict__, "name_published_in_year": name_published_in_year},
            taxonomic_status=(usage.get("taxonomicStatus") or "").capitalize(),
            authors=usage.get("authorship") or "",
            synonym=bool(usage.get("synonym")),
            synonyms_concat=synonyms_concat,
            distribution_concat=distribution_concat,
        )

    @staticmethod
    def _update_taxon_from_gbif_api(
        result: _ParsedIpniSearchResult,
    ) -> _ParsedApiSearchResult:
        """For the supplied search result entry, fetch additional information from GBIF API."""
        # # POWO uses LSID as ID just like IPNI
        #
        # # powo_lookup = powo.lookup(result.lsid, include=["distribution"])
        # # pykew is lightly maintained and the POWO API is undocumented and can change without
        # # notice; this is a workaround that needs to be fixed sometimes
        # # update: powo returns 403 from server, 200 on local test system
        # # e.g. https://powo.science.kew.org/api/2/taxon/urn:lsid:ipni.org:names:77095488-1?fields=distribution
        # # no api available, pykew 8y not maintained -> no solution, yet
        # try:
        #     resp = requests.get(
        #         f"https://powo.science.kew.org/api/2/taxon/{result.lsid}",
        #         params={"fields": "distribution"},
        #         headers={"User-Agent": "your-app-name/1.0 (contact@example.com)"},
        #         timeout=10,
        #     )
        #     resp.raise_for_status()
        #     powo_lookup = resp.json()
        #
        # except HTTPError as e:
        #     logger.error(f"HTTP error occurred while fetching POWO data for LSID {result.lsid}: {e}")
        #     return _ParsedApiSearchResult(
        #         **result.__dict__,
        #         # basionym='',
        #         taxonomic_status='',
        #         authors='',
        #         synonym=False,
        #         synonyms_concat='',
        #         distribution_concat='',
        #     )
        #
        # if "error" in powo_lookup:
        #     throw_exception(f"No Plants of the World result for LSID {result.lsid}")
        #
        # # basionym = powo_lookup["basionym"].get("name") if "basionym" in powo_lookup else None
        #
        # ext_result = _ParsedApiSearchResult(
        #     **result.__dict__,
        #     # basionym=basionym,
        #     taxonomic_status=powo_lookup.get("taxonomicStatus"),
        #     authors=powo_lookup.get("authors"),
        #     synonym=powo_lookup.get("synonym"),
        #     synonyms_concat=get_accepted_synonym_label(powo_lookup),
        #     distribution_concat=get_concatenated_distribution(powo_lookup),
        # )
        #
        # if "name_published_in_year" in powo_lookup:
        #     ext_result.name_published_in_year = powo_lookup["name_published_in_year"]

        gbif_result = ApiSearcher._fetch_from_gbif(result)
        if not gbif_result:
            logger.warning(
                "[GBIF TEST] No IPNI-dataset match found for LSID %s (name=%r).",
                result.lsid, result.name,
            )

        return gbif_result

import logging

from fastapi.concurrency import run_in_threadpool
from pykew import ipni as ipni
from pykew import powo as powo
from pykew.ipni_terms import Name

from plants import settings
from plants.exceptions import TooManyResultsError
from plants.modules.biodiversity.taxonomy_shared_functions import (
    create_distribution_concat, create_synonym_label_if_only_a_synonym)
from plants.modules.taxon.enums import FBRank
from plants.modules.taxon.models import Taxon
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.message_services import throw_exception

logger = logging.getLogger(__name__)


class TaxonomySearch:
    def __init__(
        self,
        include_external_apis: bool,
        search_for_genus_not_species: bool,
        taxon_dal: TaxonDAL,
    ):
        self.include_external_apis = include_external_apis
        self.search_for_genus_not_species = search_for_genus_not_species
        self.taxon_dal = taxon_dal

    async def search(self, taxon_name_pattern: str) -> list[dict]:
        """Search for a taxon name via pattern, first in local database, then
        in external APIs merge results from local database and external
        APIs."""
        # search for taxa already in the database
        local_results = await self._query_taxa_in_local_database(
            taxon_name_pattern=f"%{taxon_name_pattern}%",
            search_for_genus_not_species=self.search_for_genus_not_species,
        )
        results = local_results[:]

        # optionally, search in external biodiversity databases "ipni" and "powo"
        if self.include_external_apis:
            api_searcher = ApiSearcher(
                search_for_genus_not_species=self.search_for_genus_not_species
            )

            kew_results = await run_in_threadpool(
                api_searcher.search_taxa_in_external_apis,
                plant_name_pattern=taxon_name_pattern,  # no %/* required here
                local_results=local_results,
            )

            # kew_results = api_searcher.search_taxa_in_external_apis(
            #     plant_name_pattern=taxon_name_pattern,  # no %/* required here
            #     local_results=local_results)

            # kew_results = self._search_taxa_in_external_apis(
            #     plant_name_pattern=taxon_name_pattern,  # no %/* required here
            #     local_results=local_results)
            results.extend(kew_results)
        return results

    @staticmethod
    def _get_search_result_from_db_taxon(taxon: Taxon) -> dict:
        search_result_entry = {
            # 'source': BSearchResultSource.SOURCE_PLANTS_DB,
            "id": taxon.id,
            "in_db": True,
            "count": len([p for p in taxon.plants if p.active]),
            "count_inactive": len([p for p in taxon.plants if not p.active]),
            "is_custom": taxon.is_custom,
            "synonym": taxon.synonym,
            "authors": taxon.authors,
            "family": taxon.family,
            "name": taxon.name,
            "rank": taxon.rank,
            "taxonomic_status": taxon.taxonomic_status,
            "lsid": taxon.lsid,  # if not taxon.is_custom else None,
            # 'powo_id': taxon.powo_id,
            "genus": taxon.genus,
            "species": taxon.species,
            "infraspecies": taxon.infraspecies,
            "hybrid": taxon.hybrid,
            "hybridgenus": taxon.hybridgenus,
            "custom_suffix": taxon.custom_suffix,
            "custom_rank": taxon.custom_rank,
            "custom_infraspecies": taxon.custom_infraspecies,
            "cultivar": taxon.cultivar,
            "affinis": taxon.affinis,
            "name_published_in_year": taxon.name_published_in_year,
            "basionym": taxon.basionym,
            # 'phylum': taxon.phylum,
            "synonyms_concat": taxon.synonyms_concat
            # if taxon.distribution_concat and len(taxon.distribution_concat) >= 150:
            #     result['distribution_concat'] = query.distribution_concat[:147] + '...'
        }
        return search_result_entry

    async def _query_taxa_in_local_database(
        self, taxon_name_pattern: str, search_for_genus_not_species: bool
    ) -> list[dict]:
        """Searches term in local botany database and returns results in web-
        format."""
        if search_for_genus_not_species:
            taxa = await self.taxon_dal.get_taxa_by_name_pattern(
                taxon_name_pattern, FBRank.GENUS
            )
        else:
            taxa = await self.taxon_dal.get_taxa_by_name_pattern(taxon_name_pattern)

        results = []
        for taxon in taxa:
            result = self._get_search_result_from_db_taxon(taxon)
            results.append(result)

        logger.info(
            "Found query term in plants taxon database."
            if results
            else "Query term not found in plants taxon database."
        )
        return results


class ApiSearcher:
    def __init__(self, search_for_genus_not_species: bool):
        self.search_for_genus_not_species = search_for_genus_not_species

    def search_taxa_in_external_apis(
        self,
        plant_name_pattern: str,
        local_results: list,
    ) -> list[dict]:
        """Searches term in kew's International Plant Name Index ("IPNI") and
        Plants of the World ("POWO"); ignores entries included in the
        local_results list."""
        # First step: search in the International Plant Names Index (IPNI) which has slightly more items than POWO
        results, lsid_in_powo = self._search_taxa_in_ipni_api(
            plant_name_pattern=plant_name_pattern, ignore_local_db_results=local_results
        )

        # Second step: for each IPNI result, search in POWO for more details if available
        bad_todo = []
        for result in results[:]:  # can't remove from oneself
            result: dict

            # for those entries without POWO data, we add a warning concerning acceptance status first
            if result["lsid"] not in lsid_in_powo:
                results.remove(result)
                bad_todo.append(result)
                continue
                # result['synonyms_concat'] = 'Status unknown, no entry in POWO'

            self._update_taxon_from_powo_api(result)

        logger.info(
            f'Found {len(results)} results from IPNI/POWO search for search term "{plant_name_pattern}".'
        )
        return results

    def _search_taxa_in_ipni_api(
        self, plant_name_pattern: str, ignore_local_db_results: list[dict]
    ) -> tuple[list[dict], set]:
        """Search for species / genus pattern in Kew's IPNI database skip if
        already in local database might raise TooManyResultsError."""
        results = []
        lsid_in_powo = set()

        if not self.search_for_genus_not_species:
            ipni_search = ipni.search(plant_name_pattern)
        else:
            ipni_query = {Name.genus: plant_name_pattern, Name.rank: "gen."}
            ipni_search = ipni.search(ipni_query)
        if ipni_search.size() > settings.plants.taxon_search_max_results:
            msg = f'Too many search results for search term "{plant_name_pattern}": {ipni_search.size()}'
            raise TooManyResultsError(msg)

        elif ipni_search.size() == 0:
            return results, lsid_in_powo

        for ipni_result in ipni_search:
            ipni_result: dict

            # check if that item is already included in the local results; if so, skip it
            if [
                r
                for r in ignore_local_db_results
                if not r["is_custom"] and r["lsid"] == ipni_result["fqId"]
            ]:
                continue

            # treat infraspecific taxa
            # a taxon may have 0 or 1 infra-specific name, never multiple
            rank = ipni_result.get("rank")
            if rank == "f.":  # in some cases, forma comes as "f."
                rank = FBRank.FORMA.value
            if rank == FBRank.GENUS.value:
                species = None
                infraspecies = None
            elif rank == FBRank.SPECIES.value:
                species = ipni_result.get("species")
                infraspecies = None
            elif rank in (
                FBRank.SUBSPECIES.value,
                FBRank.VARIETY.value,
                FBRank.FORMA.value,
            ):
                species = ipni_result.get("species")
                infraspecies = ipni_result.get("infraspecies")
            else:
                raise ValueError(f"Unexpected rank {rank} for {ipni_result['fqId']}.")

            # build additional results from IPNI data
            result = {
                # 'source': BSearchResultSource.SOURCE_IPNI,
                "id": None,  # taxon id determined upon saving by database
                "in_db": False,
                "lsid": ipni_result[
                    "fqId"
                ],  # IPNI Life Sciences Identifier (used by POWO and IPNI)
                "count": 0,  # count of plants in the database
                "count_inactive": 0,
                "is_custom": False,
                "synonym": None,  # available only in POWO
                "authors": ipni_result.get("authors"),
                "name_published_in_year": ipni_result.get("publicationYear"),
                "name": ipni_result.get("name"),
                # 'taxonomic_status':  # available only in POWO
                "rank": rank,
                # 'phylum': None,  # available only in POWO
                "family": ipni_result.get("family"),
                "genus": ipni_result.get("genus"),
                "species": species,
                "infraspecies": infraspecies,
                "hybrid": ipni_result.get("hybrid"),
                "hybridgenus": ipni_result.get("hybridGenus"),
                # cultivar=  # always custom
                # affinis=  # always custom
                # 'affinis': taxon.affinis,
                # custom_suffixr=  # always custom
                # custom_rankr=  # always custom
                # custom_infraspeciesr=  # always custom
                "synonyms_concat": None,  # available only in POWO
                "distribution_concat": None,  # available only in POWO
            }
            if ipni_result.get("inPowo"):
                lsid_in_powo.add(result["lsid"])
            results.append(result)
        return results, lsid_in_powo

    @staticmethod
    def _update_taxon_from_powo_api(result: dict):
        """For the supplied search result entry, fetch additional information
        from "Plants of the World" API."""
        # POWO uses LSID as ID just like IPNI
        powo_lookup = powo.lookup(result["lsid"], include=["distribution"])
        if "error" in powo_lookup:
            throw_exception(f'No Plants of the World result for LSID {result["lsid"]}')

        # overwrite as POWO has more information
        # result['source'] = BSearchResultSource.SOURCE_IPNI_POWO
        result["in_db"]: False
        result["basionym"] = (
            powo_lookup["basionym"].get("name") if "basionym" in powo_lookup else None
        )
        result["taxonomic_status"] = powo_lookup.get("taxonomicStatus")
        result["authors"] = powo_lookup.get("authors")
        if "name_published_in_year" in powo_lookup:
            result["name_published_in_year"] = powo_lookup["name_published_in_year"]
        result["synonym"] = powo_lookup.get("synonym")
        if powo_lookup.get("synonym"):
            if "accepted" in powo_lookup and (
                accepted_name := powo_lookup["accepted"].get("name")
            ):
                result["synonyms_concat"] = create_synonym_label_if_only_a_synonym(
                    accepted_name
                )
            else:
                result["synonyms_concat"] = "Accepted: unknown"

        # add information only available at POWO
        # result['phylum'] = powo_lookup.get('phylum')
        result["distribution_concat"] = create_distribution_concat(powo_lookup)

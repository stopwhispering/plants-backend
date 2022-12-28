import logging

from pykew import ipni as ipni, powo as powo
from pykew.ipni_terms import Name
from sqlalchemy.orm import Session

from plants.exceptions import TooManyResultsError
from plants.models.taxon_models import Taxon
from plants.services.taxonomy_shared_functions import create_synonym_label_if_only_a_synonym, create_distribution_concat
from plants.validation.taxon_validation import BKewSearchResultEntry, BSearchResultSource

logger = logging.getLogger(__name__)


class TaxonomySearch:
    def __init__(self, include_external_apis: bool, search_for_genus_not_species: bool, db: Session):
        self.include_external_apis = include_external_apis
        self.search_for_genus_not_species = search_for_genus_not_species
        self.db = db

    def search(self, taxon_name_pattern: str) -> list[BKewSearchResultEntry]:
        """
        might throw TooManyResultsError or JSONDecodeError
        """
        # search for taxa already in the database
        results = self._query_taxa_in_local_database(
            taxon_name_pattern=f'{taxon_name_pattern}%',
            search_for_genus_not_species=self.search_for_genus_not_species,
            db=self.db)

        # optionally search in external biodiversity databases "ipni" and "powo"
        if self.include_external_apis:
            kew_results = self._search_taxa_in_external_apis(
                plant_name_pattern=taxon_name_pattern + '*',
                local_results=results)
            results.extend(kew_results)
        return results

    @staticmethod
    def _get_search_result_from_db_taxon(taxon: Taxon) -> dict:
        search_result_entry = {
            'source': BSearchResultSource.SOURCE_PLANTS_DB,
            'id': taxon.id,
            'count': len([p for p in taxon.plants if p.active]),
            'count_inactive': len([p for p in taxon.plants if not p.active]),
            'is_custom': taxon.is_custom,
            'synonym': taxon.synonym,
            'authors': taxon.authors,
            'family': taxon.family,
            'name': taxon.name,
            'rank': taxon.rank,
            'lsid': taxon.lsid,  # if not taxon.is_custom else None,
            # 'powo_id': taxon.powo_id,
            'genus': taxon.genus,
            'species': taxon.species,
            'namePublishedInYear': taxon.name_published_in_year,
            'phylum': taxon.phylum,
            'synonyms_concat': taxon.synonyms_concat
            # if taxon.distribution_concat and len(taxon.distribution_concat) >= 150:
            #     result['distribution_concat'] = query.distribution_concat[:147] + '...'
        }
        BKewSearchResultEntry.validate(search_result_entry)
        return search_result_entry

    def _query_taxa_in_local_database(self,
                                      taxon_name_pattern: str,
                                      search_for_genus_not_species: bool,
                                      db: Session) -> list[dict]:
        """searches term in local botany database and returns results in web-format"""
        if search_for_genus_not_species:
            taxa = db.query(Taxon).filter(Taxon.name.ilike(taxon_name_pattern),  # ilike ~ case-insensitive like
                                          Taxon.rank == 'gen.').all()
        else:
            taxa = db.query(Taxon).filter(Taxon.name.ilike(taxon_name_pattern)).all()

        results = []
        for taxon in taxa:
            result = self._get_search_result_from_db_taxon(taxon)
            results.append(result)

        logger.info(f'Found query term in plants taxon database.'
                    if results else f'Query term not found in plants taxon database.')
        return results

    def _search_taxa_in_ipni_api(self,
                                 plant_name_pattern: str,
                                 local_db_results: list[BKewSearchResultEntry]) -> (
            tuple[list[BKewSearchResultEntry], set]):
        """
        search for species / genus patternin Kew's IPNI database
        skip if already in local database
        might raise TooManyResultsError
        """
        if not self.search_for_genus_not_species:
            ipni_search = ipni.search(plant_name_pattern)
        else:
            ipni_query = {Name.genus: plant_name_pattern, Name.rank: 'gen.'}
            ipni_search = ipni.search(ipni_query)
        if ipni_search.size() > 30:
            msg = f'Too many search results for search term "{plant_name_pattern}": {ipni_search.size()}'
            raise TooManyResultsError(msg)

        elif ipni_search.size() == 0:
            return [], set()

        results = []
        lsid_in_powo = set()
        for ipni_result in ipni_search:
            ipni_result: dict

            # check if that item is already included in the local results; if so, skip it
            if [r for r in local_db_results if not r['is_custom'] and r['lsid'] == ipni_result['fqId']]:
                continue

            # build additional results from IPNI data
            result = BKewSearchResultEntry.parse_obj({
                'source': BSearchResultSource.SOURCE_IPNI,
                'id': None,  # taxon id determined upon saving by database
                'count': 0,  # count of plants in the database
                'count_inactive': 0,
                'is_custom': False,
                'synonym': None,  # available only in POWO
                'authors': ipni_result.get('authors'),
                'family': ipni_result.get('family'),
                'name': ipni_result.get('name'),
                'rank': ipni_result.get('rank'),
                'lsid': ipni_result['fqId'],  # IPNI Life Sciences Identifier (used by POWO and IPNI)
                'genus': ipni_result.get('genus'),
                'species': ipni_result.get('species'),
                'namePublishedInYear': ipni_result.get('publicationYear'),
                'phylum': None,  # available only in POWO
                'synonyms_concat': None,  # available only in POWO
                'distribution_concat': None,   # available only in POWO
            })
            if ipni_result.get('inPowo'):
                lsid_in_powo.add(result.lsid)
            results.append(result)
        return results, lsid_in_powo

    @staticmethod
    def _update_taxon_from_powo_api(result: BKewSearchResultEntry) -> None:
        """
        for the supplied search result entry, fetch additional information from "Plants of the World" API
        """
        # POWO uses LSID as ID just like IPNI
        powo_lookup = powo.lookup(result.lsid, include=['distribution'])
        if 'error' in powo_lookup:
            logger.error(f'No Plants of the World result for LSID {result.lsid}')
            return

        # overwrite as POWO has more information
        result.source = BSearchResultSource.SOURCE_IPNI_POWO
        result.authors = powo_lookup.get('authors')
        if 'namePublishedInYear' in powo_lookup:
            result.namePublishedInYear = powo_lookup['namePublishedInYear']
        result.synonym = powo_lookup.get('synonym')
        if powo_lookup.get('synonym'):
            if 'accepted' in powo_lookup and (accepted_name := powo_lookup['accepted'].get('name')):
                result.synonyms_concat = create_synonym_label_if_only_a_synonym(accepted_name)
            else:
                result.synonyms_concat = 'Accepted: unknown'

        # add information only available at POWO
        result.phylum = powo_lookup.get('phylum')
        result.distribution_concat = create_distribution_concat(powo_lookup)

    def _search_taxa_in_external_apis(self,
                                      plant_name_pattern: str,
                                      local_results: list,
                                      ) -> list[BKewSearchResultEntry]:
        """searches term in kew's International Plant Name Index ("IPNI") and Plants of the World ("POWO") databases and
        returns results in web-format; ignores entries included in the local_results list"""

        # First step: search in the International Plant Names Index (IPNI) which has slightly more items than POWO
        results, lsid_in_powo = self._search_taxa_in_ipni_api(plant_name_pattern, local_results)

        # Second step: for each IPNI result, search in POWO for more details if available
        for result in results:

            # for those entries without POWO data, we add a warning concerning acceptance status first
            if result.lsid not in lsid_in_powo:
                result.synonyms_concat = 'Status unknown, no entry in POWO'

            self._update_taxon_from_powo_api(result)

        logger.info(f'Found {len(results)} results from IPNI/POWO search for search term "{plant_name_pattern}".')
        return results

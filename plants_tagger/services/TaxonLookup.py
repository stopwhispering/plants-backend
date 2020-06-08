from json import JSONDecodeError
from typing import List, Dict, Optional, Iterable
import logging
import requests

from flask_2_ui5_py import throw_exception
from pykew import ipni as ipni, powo as powo

logger = logging.getLogger(__name__)
GBIF_BASE_URL = 'https://api.gbif.org/v1/species'
DATASETKEY_IPNI = "046bbc50-cae2-47ff-aa43-729fbf53f7c5"


class TaxonLookup:
    """lookup a taxon by lsid in databases; lookup parent taxa as well"""
    def __init__(self, lsid: str, databases: Iterable[str], databases_parent: Iterable[str] = None):
        self.lsid = lsid
        self.databases = databases
        self.lookups_lsid = {}
        self.lookups_parents = []
        self.databases_parent = databases_parent if databases_parent else databases

    @staticmethod
    def _get_ipni_lookup(lsid: str) -> dict:
        try:
            return ipni.lookup_name(lsid)
        except JSONDecodeError:
            return {}

    @staticmethod
    def _get_gbif_url_for(lsid: str = None, nub_key: int = None, entity: str = 'taxon'):
        if entity == 'taxon':
            if lsid:
                return GBIF_BASE_URL + '?sourceId=' + lsid
            elif nub_key:
                """ gbif taxonomic backbone (=nub) id"""
                return GBIF_BASE_URL + '/' + str(nub_key)
            else:
                throw_exception('Neither lsid nor gbif key supplied or bad combination.')
        elif entity == 'related':
            return GBIF_BASE_URL + '/' + str(nub_key) + '/related'

    def _get_gbif_nub(self, lsid: str) -> Optional[int]:
        """find gbif key (= nub) by searching for lsid via gbif rest api"""
        url = self._get_gbif_url_for(lsid)
        resp = requests.get(url, headers={"Content-Type": "application/json"})
        if resp.status_code != 200 and resp.status_code != 304:
            logger.warning(f'Bad response for gbif lookup lsid: {resp.status_code} / {lsid}')
            return None
        results = resp.json()
        if not results.get('results'):
            return None
        return results['results'][0].get('nubKey')

    def _get_gbif_lookup(self, lsid: str) -> dict:
        """lookup gbif database (meta database)
        at first find ipni entry there via lsid, where we get the gbif id
        which is required for finding gbif collection entry"""
        # find gbif nubkey
        gbif_nub = self._get_gbif_nub(lsid=lsid)
        if not gbif_nub:
            return {}

        # get gbif lookup
        url = self._get_gbif_url_for(nub_key=gbif_nub)
        resp = requests.get(url, headers={"Content-Type": "application/json"})
        if resp.status_code != 200 and resp.status_code != 304:
            logger.warning(f'Bad response for gbif lookup nubkey: {resp.status_code} / {lsid}')
            return {}
        results = resp.json()
        return results

    @staticmethod
    def _get_powo_lookup(lsid: str) -> dict:
        powo_lookup = powo.lookup(lsid, include=['distribution'])
        return powo_lookup if 'error' not in powo_lookup else {}

    def _lookup_lsid(self, lsid) -> Dict[str, Dict]:
        """lookup supplied lsid in all databases; return as dict"""
        results = {'_lsid': lsid}
        for db in self.databases:
            if db == 'ipni':
                results['ipni'] = self._get_ipni_lookup(lsid)
            elif db == 'powo':
                results['powo'] = self._get_powo_lookup(lsid)
            elif db == 'gbif':
                results['gbif'] = self._get_gbif_lookup(lsid)
        return results

    def lookup_taxon(self) -> Dict[str, Dict]:
        """lookup taxon lsid; store and return results"""
        self.lookups_lsid = self._lookup_lsid(self.lsid)
        return self.lookups_lsid

    def _get_parent_lsid_from_gbif(self, gbif_lookup: dict) -> Optional[str]:
        """via gbif rest api, find parent taxon's lsid"""
        if gbif_lookup.get('parentKey'):
            url = self._get_gbif_url_for(nub_key=gbif_lookup['parentKey'], entity='related')
            resp = requests.get(url, headers={"Content-Type": "application/json"})
            if resp.status_code != 200 and resp.status_code != 304:
                logger.warning(f'Bad response for gbif lookup nubkey: {resp.status_code} / {gbif_lookup["parentKey"]}')
                return
            results = resp.json()
            if results.get('results'):
                res2 = results['results']
                res3 = [r for r in res2 if r.get('datasetKey') == DATASETKEY_IPNI]
                if res3 and res3[0].get('taxonID').startswith('urn'):
                    return res3[0].get('taxonID')
        return

    def _get_parent_lsid_from_lookups(self, lookups: Dict[str, dict]) -> Optional[str]:
        """supply with dict mapping db_name to lookup; receive parent lsid"""
        for db in self.databases_parent:
            if db == 'ipni':
                if lookups['ipni'].get('parent') and \
                        lookups['ipni'].get('parent')[0].get('fqId'):
                    return lookups['ipni'].get('parent')[0].get('fqId')
            elif db == 'powo':
                if lookups['powo'].get('classification') and \
                        lookups['powo'].get('classification')[0].get('fqId'):
                    return lookups['powo'].get('classification')[0].get('fqId')
            elif db == 'gbif':
                # a bit more difficult
                lsid_tmp = self._get_parent_lsid_from_gbif(gbif_lookup=lookups['gbif'])
                if lsid_tmp:
                    return lsid_tmp
        return None

    def _is_empty(self, lookups: Dict[str, dict]):
        """returns true if lookup contains only empty dicts for each database name"""
        for db in self.databases:
            if len(lookups[db]) > 0:
                return False
        return True

    def lookup_parents(self) -> List[Dict]:
        """lookup lsid's parent taxa; requires lookup() to have already occured"""

        # get immediate parent of taxon itself
        parent_lsid = self._get_parent_lsid_from_lookups(self.lookups_lsid)
        if not parent_lsid:
            logger.warning(f'No parent taxa found for: {self.lsid}.')
            return []

        count = 0
        while count < 6 and parent_lsid:
            lookups = self._lookup_lsid(parent_lsid)
            if self._is_empty(lookups):
                break
            self.lookups_parents.append(lookups)
            new_parent_lsid = self._get_parent_lsid_from_lookups(lookups)
            if new_parent_lsid == parent_lsid:
                break
            parent_lsid = new_parent_lsid
            count += 1

        return self.lookups_parents

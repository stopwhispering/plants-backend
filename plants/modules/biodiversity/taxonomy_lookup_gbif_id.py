import logging
import urllib.parse
from typing import Final, Optional

import requests  # todo replace with async http client
from bs4 import BeautifulSoup
from pygbif import species
from wikidata.client import Client

URL_PATTERN_WIKIDATA_SEARCH: Final[
    str
] = r"https://www.wikidata.org/w/index.php?search={}"
WIKIDATA_IPNI_PROPERTY_ID: Final[str] = "P961"
WIKIDATA_GBIF_PROPERTY_ID: Final[str] = "P846"
WIKIDATA_POWO_PROPERTY_ID: Final[str] = "P5037"

IPNI_DATASET_KEY: Final[str] = "046bbc50-cae2-47ff-aa43-729fbf53f7c5"
GBIF_REST_API_RELATED_NAME_USAGES: Final[str] = (
    "https://api.gbif.org/v1/species/{nubKey}/related?datasetKey={" "datasetKey}"
)

logger = logging.getLogger(__name__)


class GBIFIdentifierLookup:
    def lookup(self, taxon_name: str, lsid: str) -> str | None:
        gbif_id = self._gbif_id_from_gbif_api(
            taxon_name=taxon_name, lsid=lsid
        ) or self._get_gbif_id_from_wikidata(lsid=lsid)
        return gbif_id

    @staticmethod
    def _gbif_id_from_rest_api(nub_key: int, lsid: str) -> Optional[int]:
        url = GBIF_REST_API_RELATED_NAME_USAGES.format(
            nubKey=nub_key, datasetKey=IPNI_DATASET_KEY
        )
        resp = requests.get(url)
        if resp.status_code != 200:
            logger.error(f"Error at GET request for GBIF REST API: {resp.status_code}")
            return
        if resp.json().get("results"):
            # find our plant's record in ipni dataset at gbif
            ipni_record = next(
                (r for r in resp.json().get("results") if r.get("taxonID") == lsid), {}
            )
            # ... and make sure it has the correct identifier; if it has, we know we have the correct gbif id (=nubKey)
            if ipni_record.get("taxonID") == lsid:
                return nub_key

    def _gbif_id_from_gbif_api(self, taxon_name: str, lsid: str) -> Optional[int]:
        """
        the GBIF API does not allow searching by other database's taxonId; therefore, we search by
           botanical name and IPNI dataset key, then we compare the (external) taxonId"; if we have a match, we
           can return the GBIF taxon ID
           unfortunately, the attribute taxon ID (= Kew identifier LSID) is not included in the results sometimes (e.g.
           Aloiampelos ciliaris, nubKey 9527904, although the website and the REST API has it; therefore we use
           the latter if not found to verify the GBIF record.
        """
        logger.info(f"Searching IPNI Dataset at GBIF for {taxon_name} to get GBIF ID.")
        lookup = species.name_lookup(q=taxon_name, datasetKey=IPNI_DATASET_KEY)
        if not lookup.get("results"):
            logger.info("No results on IPNI Dataset at GBIF.")
            return None

        results_compared = [r for r in lookup["results"] if r.get("taxonID") == lsid]
        if results_compared:
            # nub is the name of the internal gbif database
            gbif_id = results_compared[0].get("nubKey") or None
            logger.info(f"Found GBIF ID in IPNI Dataset at GBIF: {gbif_id}.")
            return gbif_id

        # didn't find via PyGbif; try REST API directly
        logger.info(
            "No results on IPNI Dataset at GBIF matching IPNI ID via PyGbif. Trying REST API."
        )
        for r in (r for r in lookup["results"] if r.get("nubKey")):
            gbif_id = self._gbif_id_from_rest_api(nub_key=r.get("nubKey"), lsid=lsid)
            if gbif_id:
                return gbif_id

        return None

    @staticmethod
    def _get_gbif_id_from_wikidata(lsid: str) -> Optional[int]:
        """get mapping from ipni id to gbif id from wikidata; unfortunately, the wikidata api is defect, thus we parse
        using beautifulsoup4"""
        # fulltext-search wikidata for ipni id
        lsid_number = lsid[lsid.rfind(":") + 1 :]
        lsid_number_exact = f'"{lsid_number}"'
        logger.debug(f"Beginning search for {lsid_number_exact}")
        lsid_encoded = urllib.parse.quote(lsid_number_exact)
        search_url = URL_PATTERN_WIKIDATA_SEARCH.format(lsid_encoded)
        page = requests.get(search_url)
        soup = BeautifulSoup(page.content, "html.parser")

        # get search results
        tag_search_results_list = soup.find("ul", class_="mw-search-results")
        if not tag_search_results_list:
            logger.warning("No wikidata search results. Aborting.")
            return

        tag_search_results = tag_search_results_list.find_all("li")
        if not tag_search_results:
            logger.warning("No wikidata search results. Aborting.")
            return
        logger.debug(f"Search results on wikidata: {len(tag_search_results)}")

        # use first (use that with a correct subheader/description; there are often two, whatever the reason is)
        tag_search_result = None
        for t in tag_search_results:
            desc = t.find("span", class_="wb-itemlink-description")
            if desc and desc.getText() == "species of plant":
                tag_search_result = t
                break
        if not tag_search_result:
            tag_search_result = tag_search_results[0]

        result_text_full = tag_search_result.getText()
        pos = result_text_full.find(" (Q")
        logger.debug(f"Navigating to search result: {result_text_full[:pos]}")
        wikidata_entity_raw = tag_search_result.find(
            "span", class_="wb-itemlink-id"
        ).getText()  # e.g. (Q15482666)
        wikidata_entity = wikidata_entity_raw.replace("(", "").replace(")", "")

        # once we have the wikidata entity, we can use the python api
        wikidata_object = Client().get(wikidata_entity, load=True)

        # verify we have the correct plant by comparing with our ipni id
        correct_found = False
        # noinspection PyUnresolvedReferences
        ipni_claim = wikidata_object.data["claims"].get(WIKIDATA_IPNI_PROPERTY_ID)
        if ipni_claim:
            lsid_found = ipni_claim[0]["mainsnak"]["datavalue"]["value"]
            if lsid_found == lsid_number:
                correct_found = True

        # alternatively, wikidata might have the plants of the world online (powo) id, which is the same
        # (sometimes, ipni is a synonym and powo is the correct one)
        # noinspection PyUnresolvedReferences
        powo_claim = wikidata_object.data["claims"].get(WIKIDATA_POWO_PROPERTY_ID)
        if powo_claim:
            lsid_found_raw = powo_claim[0]["mainsnak"]["datavalue"]["value"]
            lsid_found = lsid_found_raw[lsid.rfind(":") + 1 :]
            if lsid_found == lsid_number:
                correct_found = True

        if not powo_claim and not ipni_claim:
            logger.warning("Could not determine correctness of site. Aborting.")
            return

        if not correct_found:
            logger.warning("Wikidata site is not the correct one. Aborting.")
            return

        # finally, get the gbif id
        # noinspection PyUnresolvedReferences
        gbif_claim = wikidata_object.data["claims"].get(WIKIDATA_GBIF_PROPERTY_ID)
        if not gbif_claim:
            logger.warning("Wikidata site found, but contains no gbif id.")
            return

        gbif_id = gbif_claim[0]["mainsnak"]["datavalue"]["value"]
        logger.info(f"GBIF Identifier found on Wikidata: {gbif_id}")

        return int(gbif_id)

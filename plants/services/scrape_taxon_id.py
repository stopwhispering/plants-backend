import requests
import urllib.parse
import logging
from bs4 import BeautifulSoup
from typing import Optional
from wikidata.client import Client
from pygbif import species

URL_PATTERN_WIKIDATA_SEARCH = r'https://www.wikidata.org/w/index.php?search={}'
WIKIDATA_IPNI_PROPERTY_ID = 'P961'
WIKIDATA_GBIF_PROPERTY_ID = 'P846'
WIKIDATA_POWO_PROPERTY_ID = 'P5037'

IPNI_DATASET_KEY = "046bbc50-cae2-47ff-aa43-729fbf53f7c5"

logger = logging.getLogger(__name__)


def gbif_id_from_gbif_api(botanical_name: str, ipni_id: str) -> Optional[int]:
    """the gbif api does not allow searching by other database's taxonId; therefore, we search by
    botanical name and ipni dataset key, then we compare the (external) taxonId"; if we have a match, we
    can return the gbif taxon id"""
    logger.info(f'Searching IPNI Dataset for {botanical_name} to get GBIF ID.')
    lookup = species.name_lookup(q=botanical_name, datasetKey=IPNI_DATASET_KEY)
    if not lookup.get('results'):
        return None

    results_compared = [r for r in lookup['results'] if r.get('taxonID') == ipni_id]
    if not results_compared:
        return None

    # nub is the name of the internal gbif database
    gbif_id = results_compared[0].get('nubKey') or None
    return gbif_id


def get_gbif_id_from_wikidata(ipni_id: str) -> Optional[int]:
    """get mapping from ipni id to gbif id from wikidata; unfortunately, the wikidata api is defect, thus we parse
    using beautifulsoup4"""
    # fulltext-search wikidata for ipni id
    ipni_id_number = ipni_id[ipni_id.rfind(':')+1:]
    ipni_id_number_exact = f"\"{ipni_id_number}\""
    logger.debug(f'Beginning search for {ipni_id_number_exact}')
    ipni_id_encoded = urllib.parse.quote(ipni_id_number_exact)
    search_url = URL_PATTERN_WIKIDATA_SEARCH.format(ipni_id_encoded)
    page = requests.get(search_url)
    soup = BeautifulSoup(page.content, 'html.parser')

    # get search results
    tag_search_results_list = soup.find('ul', class_="mw-search-results")
    if not tag_search_results_list:
        logger.warning('No wikidata search results. Aborting.')
        return

    tag_search_results = tag_search_results_list.find_all('li')
    if not tag_search_results:
        logger.warning('No wikidata search results. Aborting.')
        return
    logger.debug(f'Search results on wikidata: {len(tag_search_results)}')

    # use first (use that with a correct subheader/description; there are often two, whatever the reason is)
    tag_search_result = None
    for t in tag_search_results:
        desc = t.find('span', class_='wb-itemlink-description')
        if desc and desc.getText() == 'species of plant':
            tag_search_result = t
            break
    if not tag_search_result:
        tag_search_result = tag_search_results[0]

    result_text_full = tag_search_result.getText()
    pos = result_text_full.find(' (Q')
    logger.debug(f'Navigating to search result: {result_text_full[:pos]}')
    wikidata_entity_raw = tag_search_result.find('span', class_="wb-itemlink-id").getText()  # e.g. (Q15482666)
    wikidata_entity = wikidata_entity_raw.replace('(', '').replace(')', '')

    # once we have the wikidata entity, we can use the python api
    wikidata_object = Client().get(wikidata_entity, load=True)

    # verify we have the correct plant by comparing with our ipni id
    correct_found = False
    # noinspection PyUnresolvedReferences
    ipni_claim = wikidata_object.data['claims'].get(WIKIDATA_IPNI_PROPERTY_ID)
    if ipni_claim:
        ipni_id_found = ipni_claim[0]['mainsnak']['datavalue']['value']
        if ipni_id_found == ipni_id_number:
            correct_found = True

    # alternatively, wikidata might have the plants of the world online (powo) id, which is the same
    # (sometimes, ipni is a synonym and powo is the correct one)
    # noinspection PyUnresolvedReferences
    powo_claim = wikidata_object.data['claims'].get(WIKIDATA_POWO_PROPERTY_ID)
    if powo_claim:
        powo_id_found_raw = powo_claim[0]['mainsnak']['datavalue']['value']
        powo_id_found = powo_id_found_raw[ipni_id.rfind(':') + 1:]
        if powo_id_found == ipni_id_number:
            correct_found = True

    if not powo_claim and not ipni_claim:
        logger.warning('Could not determine correctness of site. Aborting.')
        return
    elif not correct_found:
        logger.warning('Wikidata site is not the correct one. Aborting.')
        # todo: try other search results?
        return

    # finally, get the gbif id
    # noinspection PyUnresolvedReferences
    gbif_claim = wikidata_object.data['claims'].get(WIKIDATA_GBIF_PROPERTY_ID)
    if not gbif_claim:
        logger.warning('Wikidata site found, but contains no gbif id.')
        return

    gbif_id = gbif_claim[0]['mainsnak']['datavalue']['value']
    logger.info(f'GBIF Identifier found on Wikidata: {gbif_id}')

    return int(gbif_id)

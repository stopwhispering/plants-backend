import requests
import urllib.parse
import logging
from bs4 import BeautifulSoup
from typing import Optional
from wikidata.client import Client

URL_PATTERN_WIKIDATA_SEARCH = r'https://www.wikidata.org/w/index.php?search={}'
WIKIDATA_IPNI_PROPERTY_ID = 'P961'
WIKIDATA_GBIF_PROPERTY_ID = 'P846'
WIKIDATA_POWO_PROPERTY_ID = 'P5037'

logger = logging.getLogger(__name__)


def get_gbif_id_from_ipni_id(ipni_id: Optional[int]) -> object:
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
    ipni_claim = wikidata_object.data['claims'].get(WIKIDATA_IPNI_PROPERTY_ID)
    if ipni_claim:
        ipni_id_found = ipni_claim[0]['mainsnak']['datavalue']['value']
        if ipni_id_found == ipni_id_number:
            correct_found = True

    # alternatively, wikidata might have the plants of the world online (powo) id, which is the same
    # (sometimes, ipni is a synonym and powo is the correct one)
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
    gbif_claim = wikidata_object.data['claims'].get(WIKIDATA_GBIF_PROPERTY_ID)
    if not gbif_claim:
        logger.warning('Wikidata site found, but contains no gbif id.')
        return

    gbif_id = gbif_claim[0]['mainsnak']['datavalue']['value']
    logger.info(f'GBIF Identifier found on Wikidata: {gbif_id}')

    return int(gbif_id)

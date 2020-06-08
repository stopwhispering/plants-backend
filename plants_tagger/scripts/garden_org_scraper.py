# fully function and working for lots of botanical names
# but garden.org has no open api and information is not systematic but seems to be maintained by users

import requests
import logging
from bs4 import BeautifulSoup
from requests.compat import urljoin

from plants_tagger.util.logger import configure_root_logger
from plants_tagger.util.rest import get_fake_headers

GARDEN_SEARCH = r'https://garden.org/search/index.php?q={}'

logger = logging.getLogger(__name__)


class GardenScraper:
    def __init__(self):
        self.soup = None
        self.error = None
        logger.debug(f'Instantiated Garden scraper.')

    @staticmethod
    def parse_plant_site(url):
        """scrapes plant site and parses information from rows"""
        page = requests.get(url, headers=get_fake_headers())
        soup = BeautifulSoup(page.content, 'html.parser')

        # general plant information
        information = {}
        tag = soup.find(lambda t: t.name == 'caption' and t.get_text().startswith('General Plant Information'))
        if not tag:
            logger.warning(f'No general information section found at {url}')
        else:
            table = tag.parent
            rows = table.find_all('tr')
            for row in rows:
                key = row.find('td').get_text().strip().replace(':', '')
                value = row.find('td').find_next_sibling().get_text().strip()
                information[key] = value

        # get vernacular names
        vernacular_names = []
        tag = soup.find(lambda t: t.name == 'caption' and t.text == 'Common names:')
        if not tag:  # some plants don't have a common names section
            logger.debug(f'No vernacular names section found at {url}.')
        else:
            table = tag.parent
            rows = table.find_all('tr')
            for row in rows:
                tag = row.find_all('td')[1]
                vernacular_names.append(tag.get_text().strip())

        logger.info(f'Returning {len(information)} general information items and {len(vernacular_names)} vernacular '
                    f'names from {url}.')
        return information, vernacular_names

    @staticmethod
    def search(search_term):
        """search, then parse and return results"""
        logger.info(f'Searching at garden.org for search term: {search_term}.')

        url = GARDEN_SEARCH.format(search_term.replace(' ', '+'))
        page = requests.get(url, headers=get_fake_headers())
        soup = BeautifulSoup(page.content, 'html.parser')

        # get search results table tag
        tag = soup.find(lambda t: t.name == 'caption' and t.text == 'Results from our plant database:')
        if not tag:
            raise ValueError(f'No results found for search term {search_term}.')
        table = tag.parent

        # get all result rows
        tag = table.find_all('tr')
        rows = tag[1:]

        # parse botanical name site url and thumbnail image url from each result row
        results = []
        for row in rows:
            result = {}
            tag = row.find(lambda t: t.name == 'td' and t.attrs.get('data-th') == 'Plant')
            result['name'] = tag.get_text().strip()
            href_site = tag.find('a').attrs.get('href')
            result['url_site'] = urljoin(GARDEN_SEARCH, href_site)

            tag = row.find(lambda t: t.name == 'td' and t.attrs.get('data-th') == 'Thumbnail')
            if tag.find('img'):  # thumbnail not available for all search results
                href_thumbnail = tag.find('img').attrs.get('src')
                result['url_thumbnail'] = urljoin(GARDEN_SEARCH, href_thumbnail)

            results.append(result)

        logger.info(f'Returning {len(results)} search results for term "{search_term}", '
                    f'{len([s for s in results if s.get("url_thumbnail")])} of them having a thumbnail.')
        return results


if __name__ == '__main__':
    configure_root_logger()
    garden_scraper = GardenScraper()
    try:
        # search_results = garden_scraper.search('Aeonium tabuliforme')
        x = garden_scraper.parse_plant_site(r'https://garden.org/plants/view/86808/Silver-Jade-Crassula-arborescens/')
        a = 1
    except ValueError as e:   # todo
        logger.warning(e.args[0])
        a = 1

import requests
import logging
from bs4 import BeautifulSoup
from requests.compat import urljoin
import pandas as pd
import pickle
from plants_tagger.util.logger import configure_root_logger

URL_SEARCH = r'http://pza.sanbi.org/search?s='
URL_SAMPLE = r'http://pza.sanbi.org/gasteria-acinacifolia'
URL_SAMPLE2 = r'http://pza.sanbi.org/gasteria-disticha'

logger = logging.getLogger(__name__)


class PzaScraper:
    def __init__(self):
        self.soup = None
        self.error = None
        logger.debug(f'Instantiated PZA scraper.')

    @staticmethod
    def _get_search_result_urls(plant: str):
        url = URL_SEARCH + plant
        sites = [url]
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        ul_pages = soup.find("ul", {"class": "pager"})
        other_pages = ul_pages.find_all("li", {"class": "pager-item"})
        other_pages_urls = [p.find('a').get('href') for p in other_pages]
        sites.extend([urljoin(url, u) for u in other_pages_urls])
        return sites

    def _get_plant_urls(self, search_result_urls, plant):
        plant_urls = []
        for url in search_result_urls:
            page = requests.get(url)
            soup = BeautifulSoup(page.content, 'html.parser')
            result_divs = soup.findAll("div", {"class": "result-item"})
            plant_urls.extend([r.find('a').get('href') for r in result_divs])

        # filter out other plant results
        return [p for p in plant_urls if p.find(plant.lower()) >= 0]


    def search_plant_urls(self, plant: str = 'Gasteria'):
        search_result_urls = self._get_search_result_urls(plant)
        plant_urls = self._get_plant_urls(search_result_urls, plant)
        return plant_urls

    def _scrape_plant_url(self, url):
        # logger.info('Scraping: ' + url)
        plant = {'url': url}
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        author = soup.find("div", {"class": "author-info"}).get_text().strip()
        plant['name'] = author[:author.find('Family')].strip()
        plant['common_names'] = author[author.find('Common names: ') + 14:].split(';')

        attributes_bar = soup.find("div", {"class": "attributes"})
        attributes = attributes_bar.find_all('p')
        attributes2 = [a.get_text().strip().split(':') for a in attributes]
        attributes3 = {a[0].strip(): a[1].strip() for a in attributes2}
        plant['attributes'] = attributes3

        special_features = attributes_bar.find_all("div", {"class": "feature-item"})
        special_features2 = [s.get_text().strip() for s in special_features]
        special_features3 = {s: True for s in special_features2}
        plant['special_features'] = special_features3

        horticultural = attributes_bar.find('div', {"class": "special-features"})
        horticultural2 = horticultural.find_all('h4')
        horticultural3 = [h.get_text().strip() for h in horticultural2]
        plant['horticultural_zones'] = {h: True for h in horticultural3}

        article = soup.find('div', {'class': 'full-articles'})
        headers = article.find_all('h3', {'class': ''})
        plant['texts'] = {}
        for header in headers:
            header2 = header.get_text().strip()
            if header2.startswith('Growing'):
                header2 = 'Growing'
            if header2 != 'References':
                text = header.find_next('div')
                text2 = text.get_text().strip()
                plant['texts'][header2] = text2

        credits = soup.find('div', {'class': 'field-credits'})
        credits2 = credits.find_all('strong')
        if credits2 and len(credits2) > 1:
            credits11 = credits2[0].find('em')
            if credits11:
                credits10 = list(credits11.children)
                if len(credits10) == 3:
                    author = credits10[-1].strip()
                else:
                    author = credits2[0].get_text().strip()
                try:
                    date = list(credits2[-1].children)[-1].strip()
                except TypeError:
                    date = credits2[2].get_text().strip()
                    logger.warning('Author/Date correct?  (Case 6) ' + author + ' --- ' + date)
            else:
                author = list(credits2[0].children)[0].strip()
                date = credits2[-1].get_text().strip()
                logger.warning('Author/Date correct?  (Case 7) ' + author + ' --- ' + date)
        elif credits2:
            credits5 = credits2[0].find('em')
            if credits5:
                credits6 = list(credits5.children)
                author = credits6[0].strip()
                date = credits6[4].strip()
                logger.warning('Author/Date correct (Case 3)? ' + author + ' --- ' + date)
            else:
                credits7 = list(credits2[0].children)
                author = credits7[0].strip()
                if len(credits7) == 9:
                    date = credits7[-1].strip()
                else:
                    date = credits7[4].strip()
                logger.warning('Author/Date correct (Case 1)? ' + author + ' --- ' + date)
        else:
            credits3 = credits.find('i')
            if credits3:
                credits4 = list(credits3.children)
                if len(credits4) > 1:
                    author = credits4[0].strip()
                    date = credits4[4].strip()
                    logger.warning('Author/Date correct?  (Case 2) '+author+' --- '+date)
                else:
                    credits8 = credits.find_all('i')
                    author = credits8[0].get_text().strip()
                    date = credits8[2].get_text().strip()
                    logger.warning('Author/Date correct?  (Case 4) ' + author + ' --- ' + date)
            else:
                credits9 = credits.find('em')
                author = list(credits9.children)[0].strip()
                date = list(credits9.children)[4].strip()
                logger.warning('Author/Date correct?  (Case 5) ' + author + ' --- ' + date)

        plant['credits'] = {'author': author,
                            'date': date}

        return plant

    def scrape_plant_urls(self, urls: [str]):
        plants = []
        for i, url in enumerate(urls):
            logger.info(f'Scraping no. {i}: {url}')
            plant = self._scrape_plant_url(url)
            plants.append(plant)
        return plants

    def flatten_plants_info(self, plants: [dict]):
        results_all = []
        for plant in plants:
            results = {}
            for key, value in plant.items():
                if type(value) is str:
                    results[key] = value
                elif type(value) is list:
                    results[key] = '\n'.join(value)
                elif type(value) is dict:
                    renamed = {key+'_'+k: v for k, v in value.items()}
                    results.update(renamed)
                else:
                    print('What happened?')
                    a = 1
            results_all.append(results)
        return results_all

if __name__ == '__main__':
    configure_root_logger()
    pza_scraper = PzaScraper()
    try:
        # plant_sites = pza_scraper.search_plant_urls('Gasteria')
        # plants_info = pza_scraper.scrape_plant_urls(plant_sites)
        # plants_info = pza_scraper.scrape_plant_urls([
                                                    # 'http://pza.sanbi.org/gasteria-glauca',
                                                    #  'http://pza.sanbi.org/gasteria-koenii',
                                                    #  'http://pza.sanbi.org/gasteria-doreeniae',
                                                    #  'http://pza.sanbi.org/gasteria-pillansii'])
        # flattened = pza_scraper.flatten_plants_info(plants_info)

        # pickle.dump((
        #     plants_info,
        #     flattened,
        # ), open(r"C:\temp\plants_info.p", "wb"))



        plants_info, flattened = pickle.load(open(r"C:\temp\plants_info.p", "rb"))

        # df = pd.DataFrame(flattened)
        # df.to_excel(r'C:\temp\plants_info2.xlsx')


        # split description into sentences
        descriptions = {p['name']: p['texts']['Description'].split('.') for p in plants_info}
        descriptions2 = {key: [v.strip() for v in value] for key, value in descriptions.items()}

        # we need the same amount of items (sentences) for each plant
        max_sentences = max([len(l) for l in descriptions2.values()])
        for sentences in list(descriptions2.values()):
            sentences.extend(['']*(max_sentences-len(sentences)))
        df = pd.DataFrame(descriptions2)
        df.to_excel(r'C:\temp\plants_desc_sentences.xlsx')
        
    except ValueError as e:
        logger.warning(e.args[0])
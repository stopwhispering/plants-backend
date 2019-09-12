from json import JSONDecodeError

import pykew.ipni as ipni
from pykew.ipni_terms import Name
import pykew.powo as powo
import logging
from typing import Optional

from plants_tagger.constants import SOURCE_PLANTS, SOURCE_KEW
from plants_tagger.exceptions import TooManyResultsError, Error
from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Taxon, Distribution

logger = logging.getLogger(__name__)


def get_taxa_from_local_database(plant_name_pattern: str, search_for_genus: bool):
    """searches term in local botany database and returns results in web-format"""
    if search_for_genus:
        query_all = get_sql_session().query(Taxon).filter(Taxon.name.like(plant_name_pattern),
                                                          Taxon.rank == 'gen.').all()
    else:
        query_all = get_sql_session().query(Taxon).filter(Taxon.name.like(plant_name_pattern)).all()
    results = []
    if query_all:
        for query in query_all:
            result = {'source':              SOURCE_PLANTS,
                      'id':                  query.id,
                      'count':               len(query.plants),
                      'is_custom':           query.is_custom,
                      'synonym':             query.synonym,
                      'authors':             query.authors,
                      'family':              query.family,
                      'name':                query.name,
                      'rank':                query.rank,
                      'fqId':                query.fq_id if not query.is_custom else None,
                      'genus':               query.genus,
                      'species':             query.species,
                      'namePublishedInYear': query.name_published_in_year,
                      'phylum':              query.phylum,
                      'synonyms_concat':     query.synonyms_concat,
                      'distribution_concat': query.distribution_concat
                      }
            results.append(result)
        logger.info(f'Found query term in plants taxon database.')
    return results


def get_taxa_from_kew_databases(plant_name_pattern: str, local_results: list, search_for_genus: bool):
    """searches term in kew's international plant name index (ipni) and plants of the world (powo) databases and
    returns results in web-format; ignores entries included in the local_results list"""

    # first step: search for ids in kew's international plant names index (ipni) which has more items than powo
    if not search_for_genus:
        ipni_search = ipni.search(plant_name_pattern)
    else:
        ipni_query = {Name.genus: plant_name_pattern, Name.rank: 'gen.'}
        ipni_search = ipni.search(ipni_query)
    if ipni_search.size() > 20:
        msg = f'Too many search results for search term "{plant_name_pattern}": {ipni_search.size()}'
        raise TooManyResultsError(msg)

    elif ipni_search.size() == 0:
        return []

    kew_results = []
    for item in ipni_search:

        # check if that item is already included in the local results
        if [r for r in local_results if not r['is_custom'] and r['fqId'] == item['fqId']]:
            continue

        # build additional results from kew data
        result = {'source':              SOURCE_KEW,
                  'id':                  None,
                  'count':               None,
                  'is_custom':           False,
                  'authors':             item.get('authors'),
                  'family':              item.get('family'),
                  'name':                item.get('name'),
                  'rank':                item.get('rank'),
                  'fqId':                item['fqId'],
                  'genus':               item.get('genus'),
                  'species':             item.get('species'),
                  'namePublishedInYear': item.get('publicationYear')
                  }

        # add information from powo if available
        powo_lookup = powo.lookup(item.get('fqId'), include=['distribution'])
        if 'error' in powo_lookup:
            logger.warning(f'No kew powo result for fqId {item.get("fqId")}')
        else:
            result['phylum'] = powo_lookup.get('phylum')
            result['synonym'] = powo_lookup.get('synonym')
            result['author'] = powo_lookup.get('authors')  # overwrite as powo author has more information
            if powo_lookup.get('synonym'):
                result['synonyms_concat'] = 'Accepted: ' + powo_lookup['accepted']['name']
            else:
                result['synonyms_concat'] = get_synonyms_concat(powo_lookup)

            result['distribution_concat'] = get_distribution_concat(powo_lookup)

        kew_results.append(result)
    logger.info(f'Found {len(kew_results)} results from ipni/powo search for search term "{plant_name_pattern}".')
    return kew_results


def get_distribution_concat(powo_lookup: dict) -> Optional[str]:
    """parses areas from powo lookup dictionary into a string"""
    if 'distribution' in powo_lookup and 'natives' in powo_lookup['distribution']:
        result = ', '.join([d['name'] for d in powo_lookup[
            'distribution']['natives']]) + ' (natives)'
    else:
        result = None

    if 'distribution' in powo_lookup and 'introduced' in powo_lookup['distribution']:
        distribution_introduced = ', '.join([d['name'] for d in powo_lookup[
            'distribution']['introduced']]) + ' (introduced)'

        result = result + ', ' + distribution_introduced if \
            result else distribution_introduced

    return result


def get_synonyms_concat(powo_lookup: dict) -> Optional[str]:
    """parses synonyms from powo lookup dictionary into a string"""
    if 'synonyms' in powo_lookup and powo_lookup['synonyms']:
        return ', '.join([s['name'] for s in powo_lookup['synonyms']])
    else:
        return None


def copy_taxon_from_kew(fq_id: str,
                        has_custom_name: bool,
                        name_incl_addition: str):
    """try to find fqId in taxon table and return if existing;
    otherwise retrieve information from kew databases and create new db entry"""
    # make sure the entry really does not exist, yet
    # in case of custom name, the (conceptual) key consists of name + is_custom==True
    if has_custom_name:
        taxon = get_sql_session().query(Taxon).filter(Taxon.name == name_incl_addition,
                                                      Taxon.is_custom).first()
    # otherwise, the (conceptual) key consists of the fqId + is_custom==False
    else:
        taxon = get_sql_session().query(Taxon).filter(Taxon.fq_id == fq_id,
                                                      not Taxon.is_custom).first()
    if taxon:
        logger.warning('Taxon unexpectedly found in database.')
        return taxon

    logger.info(f'Copying taxon {fq_id} from kew databases powo and ipni.')
    # get taxon information from pew databases powo and ipni
    powo_lookup = powo.lookup(fq_id, include=['distribution'])
    ipni_lookup = ipni.lookup_name(fq_id)

    taxon = Taxon(
            name=name_incl_addition if has_custom_name else ipni_lookup.get('name'),
            is_custom=True if has_custom_name else False,
            fq_id=fq_id,

            subsp=ipni_lookup.get('subsp'),  # todo or in other?
            species=ipni_lookup.get('species'),
            subgen=ipni_lookup.get('subgen'),  # todo or in other?
            genus=ipni_lookup.get('genus'),
            family=ipni_lookup.get('family'),
            phylum=powo_lookup.get('phylum') if powo_lookup else None,
            kingdom=powo_lookup.get('kingdom') if powo_lookup else None,
            rank=ipni_lookup.get('rank'),
            taxonomic_status=powo_lookup.get('taxonomicStatus') if powo_lookup else None,
            name_published_in_year=powo_lookup.get('namePublishedInYear') if powo_lookup else ipni_lookup.get(
                    'publicationYear'),
            synonym=powo_lookup.get('synonym') if powo_lookup else None,
            authors=powo_lookup.get('authors') if powo_lookup else ipni_lookup.get('authors'),
            hybrid=ipni_lookup.get('hybrid'),
            hybridgenus=ipni_lookup.get('hybridGenus'),

            basionym=powo_lookup['basionym'].get('name') if powo_lookup and 'basionym' in powo_lookup else None,
            synonyms_concat=get_synonyms_concat(powo_lookup) if powo_lookup else None,
            distribution_concat=get_distribution_concat(powo_lookup) if powo_lookup else None
            )

    # distribution
    dist = []
    if powo_lookup and 'distribution' in powo_lookup and powo_lookup['distribution']:
        # collect native and introduced distribution into one list
        if 'natives' in powo_lookup['distribution']:
            dist.extend(powo_lookup['distribution']['natives'])
        if 'introduced' in powo_lookup['distribution']:
            dist.extend(powo_lookup['distribution']['introduced'])

    if not dist:
        logger.info(f'No distribution info found for {taxon.name}.')
    else:
        # new_records = []
        for area in dist:
            record = Distribution(name=area.get('name'),
                                  establishment=area.get('establishment'),
                                  feature_id=area.get('featureId'),
                                  tdwg_code=area.get('tdwgCode'),
                                  tdwg_level=area.get('tdwgLevel')
                                  )
            # new_records.append(record)
            taxon.distribution.append(record)

        logger.info(f'Found {len(dist)} areas for {taxon.name}.')
        # get_sql_session().add_all(new_records)

    get_sql_session().add(taxon)
    get_sql_session().commit()  # upon commit (flush), the ids are determined
    logger.info(f'Retrieved data from kew databases and created taxon {taxon.name} in database.')

    return taxon

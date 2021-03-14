import pykew.ipni as ipni
from pykew.ipni_terms import Name
import pykew.powo as powo
import logging
from typing import Optional
from sqlalchemy.orm import Session

from plants.constants import SOURCE_PLANTS, SOURCE_KEW
from plants.exceptions import TooManyResultsError
from plants.models.taxon_models import Distribution, Taxon

logger = logging.getLogger(__name__)


def get_taxa_from_local_database(plant_name_pattern: str, search_for_genus: bool, db: Session):
    """searches term in local botany database and returns results in web-format"""
    if search_for_genus:
        query_all = db.query(Taxon).filter(Taxon.name.like(plant_name_pattern),
                                           Taxon.rank == 'gen.').all()
    else:
        query_all = db.query(Taxon).filter(Taxon.name.like(plant_name_pattern)).all()
    results = []
    if query_all:
        for query in query_all:
            result = {'source':              SOURCE_PLANTS,
                      'id':                  query.id,
                      'count':               len([p for p in query.plants if p.active]),
                      'count_inactive':      len([p for p in query.plants if not p.active]),
                      'is_custom':           query.is_custom,
                      'synonym':             query.synonym,
                      'authors':             query.authors,
                      'family':              query.family,
                      'name':                query.name,
                      'rank':                query.rank,
                      'fqId':                query.fq_id if not query.is_custom else None,
                      'powo_id':             query.powo_id,
                      'genus':               query.genus,
                      'species':             query.species,
                      'namePublishedInYear': query.name_published_in_year,
                      'phylum':              query.phylum,
                      'synonyms_concat':     query.synonyms_concat}
            # if query.distribution_concat and len(query.distribution_concat) >= 150:
            #     result['distribution_concat'] = query.distribution_concat[:147] + '...'

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
    if ipni_search.size() > 30:
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
                  'id':                  None,  # determined upon saving by database
                  'count':               None,  # count of plants assigned the taxon in local extensions
                  'is_custom':           False,
                  'authors':             item.get('authors'),
                  'family':              item.get('family'),
                  'name':                item.get('name'),
                  'rank':                item.get('rank'),
                  'fqId':                item['fqId'],  # ipni id
                  'genus':               item.get('genus'),
                  'species':             item.get('species'),
                  'namePublishedInYear': item.get('publicationYear')
                  }

        # add information from powo if available
        # powo uses the same id as ipni
        powo_lookup = powo.lookup(item.get('fqId'), include=['distribution'])
        if 'error' in powo_lookup:
            logger.warning(f'No kew powo result for fqId {item.get("fqId")}')
            result['synonym'] = False
            result['powo_id'] = None
        else:
            result['powo_id'] = item.get('fqId')
            if 'namePublishedInYear' in powo_lookup:
                result['namePublishedInYear'] = powo_lookup['namePublishedInYear']
            result['phylum'] = powo_lookup.get('phylum')
            result['synonym'] = powo_lookup.get('synonym')
            result['author'] = powo_lookup.get('authors')  # overwrite as powo author has more information
            if powo_lookup.get('synonym'):
                try:
                    result['synonyms_concat'] = get_synonym_label_if_only_a_synonym(powo_lookup['accepted']['name'])
                except KeyError:
                    result['synonyms_concat'] = 'Accepted: unknown'
            else:
                result['synonyms_concat'] = get_synonyms_concat(powo_lookup)

            result['distribution_concat'] = get_distribution_concat(powo_lookup)

        kew_results.append(result)
    logger.info(f'Found {len(kew_results)} results from ipni/powo search for search term "{plant_name_pattern}".')
    return kew_results


def get_synonym_label_if_only_a_synonym(accepted_name: str):
    """little method just to make sure the same is stored in local extensions as is displayed in frontend from powo"""
    return 'Accepted: ' + accepted_name


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
                        name_incl_addition: str,
                        db: Session):
    """try to find fqId in taxon table and return if existing;
    otherwise retrieve information from kew databases and create new extensions entry"""
    # make sure the entry really does not exist, yet
    # in case of custom name, the (conceptual) key consists of name + is_custom==True
    if has_custom_name:
        taxon = db.query(Taxon).filter(Taxon.name == name_incl_addition,
                                       Taxon.is_custom is True).first()
    # otherwise, the (conceptual) key consists of the fqId + is_custom==False
    else:
        taxon = db.query(Taxon).filter(Taxon.fq_id == fq_id,
                                       Taxon.is_custom is False).first()
    if taxon:
        logger.warning('Taxon unexpectedly found in database.')
        return taxon

    logger.info(f'Copying taxon {fq_id} from kew databases powo and ipni.')
    # get taxon information from pew databases ipni and powo
    # ipni always returns a result (otherwise we wouldn't come here), powo is optional
    ipni_lookup = ipni.lookup_name(fq_id)
    powo_lookup = powo.lookup(fq_id, include=['distribution'])
    if 'error' in powo_lookup:
        powo_lookup = None

    taxon = Taxon(
            name=name_incl_addition if has_custom_name else ipni_lookup.get('name'),
            is_custom=True if has_custom_name else False,
            fq_id=fq_id,
            powo_id=powo_lookup.get('fqId') if powo_lookup else None,
            subsp=ipni_lookup.get('subsp'),
            species=ipni_lookup.get('species'),
            subgen=ipni_lookup.get('subgen'),
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
            distribution_concat=get_distribution_concat(powo_lookup) if powo_lookup else None
            )
    if powo_lookup and not powo_lookup.get('synonym'):
        taxon.synonyms_concat = get_synonyms_concat(powo_lookup)
    elif powo_lookup and powo_lookup.get('synonym'):
        taxon.synonyms_concat = get_synonym_label_if_only_a_synonym(powo_lookup['accepted']['name'])
    else:
        taxon.synonyms_concat = None

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
        for area in dist:
            record = Distribution(name=area.get('name'),
                                  establishment=area.get('establishment'),
                                  feature_id=area.get('featureId'),
                                  tdwg_code=area.get('tdwgCode'),
                                  tdwg_level=area.get('tdwgLevel')
                                  )
            taxon.distribution.append(record)

        logger.info(f'Found {len(dist)} areas for {taxon.name}.')

    db.add(taxon)
    db.commit()  # upon commit (flush), the ids are determined
    logger.info(f'Retrieved data from kew databases and created taxon {taxon.name} in database.')

    return taxon

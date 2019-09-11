import pykew.ipni as ipni
import pykew.powo as powo
import logging
from typing import Optional

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Botany2


logger = logging.getLogger(__name__)


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

        result['distribution_concat'] = result + ', ' + distribution_introduced if \
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
        taxon = get_sql_session().query(Botany2).filter(Botany2.name == name_incl_addition,
                                                        Botany2.is_custom).first()
    # otherwise, the (conceptual) key consists of the fqId + is_custom==False
    else:
        taxon = get_sql_session().query(Botany2).filter(Botany2.fq_id == fq_id,
                                                        not Botany2.is_custom).first()
    if taxon:
        logger.warning('Taxon unexpectedly found in database.')
        return taxon

    logger.info(f'Copying taxon {fq_id} from kew databases powo and ipni.')
    # get taxon information from pew databases powo and ipni
    powo_lookup = powo.lookup(fq_id, include=['distribution'])
    ipni_lookup = ipni.lookup_name(fq_id)

    taxon = Botany2(
            name=name_incl_addition if has_custom_name else ipni_lookup.get('name'),
            is_custom=True if has_custom_name else False,
            fq_id=fq_id,

            subsp=ipni_lookup.get('subsp'),  # todo or in other?
            species=ipni_lookup.get('species'),
            subgen=ipni_lookup.get('subgen'),  # todo or in other?
            genus=ipni_lookup.get('genus'),
            family=ipni_lookup.get('family'),
            phylum=powo_lookup.get('phylum'),
            kingdom=powo_lookup.get('kingdom'),
            taxonomic_status=powo_lookup.get('taxonomicStatus'),
            name_published_in_year=powo_lookup.get('namePublishedInYear'),
            synonym=powo_lookup.get('synonym'),
            authors=powo_lookup.get('authors'),
            hybrid=ipni_lookup.get('hybrid'),
            hybridgenus=ipni_lookup.get('hybridGenus'),

            basionym=powo_lookup['basionym'].get('name') if 'basionym' in powo_lookup else None,
            synonyms_concat=get_synonyms_concat(powo_lookup),
            distribution_concat=get_distribution_concat(powo_lookup)
            )

    get_sql_session().add(taxon)
    get_sql_session().commit()  # upon commit (flush), the id is determined
    logger.info('Retrieved data from kew databases and created taxon in database.')

    # todo: distirbution + coordinates in separates db tables

    return taxon

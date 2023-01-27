import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_synonym_label_if_only_a_synonym(accepted_name: str):
    """little method just to make sure the same is stored in local extensions as is displayed in frontend from powo"""
    return 'Accepted: ' + accepted_name


def create_distribution_concat(powo_lookup: dict) -> Optional[str]:
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


def create_synonyms_concat(powo_lookup: dict) -> Optional[str]:
    """parses synonyms from powo lookup dictionary into a string"""
    if 'synonyms' in powo_lookup and powo_lookup['synonyms']:
        return ', '.join([s['name'] for s in powo_lookup['synonyms']])
    else:
        return None






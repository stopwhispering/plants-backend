from typing import Optional, Dict, Tuple, List
import logging

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.taxon2 import Taxon2
from plants_tagger.models.taxon_models import Distribution

logger = logging.getLogger(__name__)


class TaxonCompileModel:
    """compile taxon model from taxon attribute values from multiple databases"""
    def __init__(self):
        self.field_config = self._get_fields_config()

    def _map_rank(self):
        pass

    @staticmethod
    def _get_fields_config():
        """ define which taxon fields are filled by which database fields in which priority"""
        # todo: move to some config file
        fields_config = {
            'rank': [('ipni', 'rank'), ('powo', 'rank')],  # note: rank mapper is applied if available
            'taxonomic_status': [('powo', 'taxonomicStatus')],
            'name_published_in_year': [('powo', 'namePublishedInYear'), ('ipni', 'publicationYear')],
            'synonym': [('powo', 'synonym')],
            'authors': [('powo', 'authors'), ('ipni', 'authors')],
            # 'basionym': [('powo', 'basionym'), ('ipni', 'basionym')],
            'hybrid': [('ipni', 'hybrid')],
            'hybridgenus': [('ipni', 'hybridGenus')],
            'scientific_name': [('gbif', 'scientificName')],
            'gbif_nub': [('gbif', 'nubKey')],
            }
        return fields_config

    @staticmethod
    def _get_name_config():
        """ define how taxon name (if not custom) is filled (by which database fields in which priority)"""
        return [('ipni', 'name'), ('powo', 'name'), ('gbif', 'canonicalName')]

    @staticmethod
    def _get_distribution_concat(powo_lookup: dict) -> Optional[str]:
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

    @staticmethod
    def _get_synonyms_concat(powo_lookup: dict, taxon_is_synonym: bool) -> str:
        """parses synonyms from powo lookup dictionary into a string"""
        if not taxon_is_synonym and powo_lookup.get('synonyms'):
            return ', '.join([s['name'] for s in powo_lookup['synonyms']])
        elif taxon_is_synonym and powo_lookup.get('accepted') and powo_lookup.get('accepted').get('name'):
            return 'Accepted: ' + powo_lookup.get('accepted').get('name')
        return ''

    def _get_name_from_config(self, lookups: Dict[str, dict]):
        config = self._get_name_config()
        for db_to_field in config:
            db = db_to_field[0]
            db_field_name = db_to_field[1]
            if db not in lookups:
                logger.warning(f'Bad field configuration. Configured db not in lookup: {db}')
                continue
            if db_field_name not in lookups[db]:
                continue
            else:
                return lookups[db][db_field_name]
        logger.error('No value found in database lookups for taxon name.')

    def _set_field_value_from_config(self, taxon: Taxon2, field_name, lookups: Dict[str, dict]):
        if not hasattr(taxon, field_name):
            logger.warning(f'Field name not found in taxon model: {field_name}')
            return

        config = self.field_config[field_name]
        for db_to_field in config:
            db = db_to_field[0]
            db_field_name = db_to_field[1]
            if db not in lookups:
                logger.warning(f'Bad field configuration. Configured db not in lookup: {db}')
                continue
            if db_field_name not in lookups[db]:
                continue
            else:
                setattr(taxon, field_name, lookups[db][db_field_name])
                return

        logger.info(f'No value found in database lookups for field name: {field_name}')

    def get_model(self,
                  lookups: Dict[str, dict],
                  overwrite: bool = False,
                  custom_name_full: str = None) -> Tuple[Taxon2, List]:
        """requires a dict mapping database name to it's lookup with key _lsid as lsid,
        generates a taxon model object and area/distribution odel objects
         returns tuple of taxon model and add list (all newly generated objects)"""

        # check if taxon already exists in our database
        lsid = lookups['_lsid']
        add_list = []
        if custom_name_full:
            taxon = get_sql_session().query(Taxon2).filter(Taxon2.name == custom_name_full,
                                                           Taxon2.is_custom == True).first()
        else:
            # otherwise, the (conceptual) key consists of the lsid + is_custom==False
            taxon = get_sql_session().query(Taxon2).filter(Taxon2.lsid == lsid,
                                                           Taxon2.is_custom == False).first()
        if taxon and not overwrite:
            return taxon, []
        elif not taxon:
            name = custom_name_full if custom_name_full else self._get_name_from_config(lookups)
            taxon = Taxon2(lsid=lsid, name=name, is_custom=True if custom_name_full else False)
            add_list.append(taxon)

        # set basic attributes
        fields_config = self._get_fields_config()
        for field_name in fields_config.keys():
            self._set_field_value_from_config(taxon, field_name, lookups)

        # basionym only from powo and nested)
        if lookups.get('powo') and lookups.get('powo').get('basionym'):
            taxon.basionym = lookups['powo']['basionym'].get('name')

        # synonyms to the taxon (only delivered from powo db)
        # if taxon itself is only a synonym, the accepted name is written to this field
        if lookups.get('powo'):
            taxon.synonyms_concat = self._get_synonyms_concat(lookups.get('powo'), taxon.synonym)

        # geographical distribution (only delivered from powo db)
        if lookups.get('powo'):
            # add as concatenated string to taxon...
            taxon.distribution_concat = self._get_distribution_concat(lookups['powo'])
            # add distribution model objects
            dist = []
            if lookups.get('powo') and lookups.get('powo').get('distribution'):
                # collect native and introduced distribution into one list
                lookup_dist = lookups.get('powo').get('distribution')
                if lookup_dist.get('natives'):
                    dist.extend(lookup_dist['natives'])
                if lookup_dist.get('introduced'):
                    dist.extend(lookup_dist['introduced'])

            if not dist:
                logger.info(f'No distribution info found for {taxon.name}.')
            else:
                records = []
                for area in dist:
                    record = Distribution(name=area.get('name'),
                                          establishment=area.get('establishment'),
                                          feature_id=area.get('featureId'),
                                          tdwg_code=area.get('tdwgCode'),
                                          tdwg_level=area.get('tdwgLevel')
                                          )
                    records.append(record)
                    add_list.append(record)
                taxon.distribution = records
                # todo in case of modification, new areas are created and old ones remain orphaned in db

                logger.info(f'Found {len(dist)} areas for {taxon.name}.')
        return taxon, add_list

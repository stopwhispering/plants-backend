from json import JSONDecodeError

from flask_restful import Resource
import logging
import pykew.ipni as ipni
import pykew.powo as powo
from flask import request
import json

from plants_tagger.constants import SOURCE_PLANTS, SOURCE_KEW
from plants_tagger.exceptions import TooManyResultsError
from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Taxon, Plant
from plants_tagger.models.taxon import copy_taxon_from_kew, get_distribution_concat, get_synonyms_concat, \
    get_taxa_from_local_database, get_taxa_from_kew_databases
from plants_tagger.models.taxon_id_mapper import get_gbif_id_from_ipni_id
from plants_tagger.util.json_helper import make_list_items_json_serializable, make_dict_values_json_serializable
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)


class TaxonResource(Resource):
    @staticmethod
    def get():
        """returns taxa from taxon database table"""
        taxa: Taxon = get_sql_session().query(Taxon).all()
        # taxon_list = [t.__dict__.copy() for t in taxa]
        # _ = [t.pop('_sa_instance_state') for t in taxon_list]  # remove instance state objects
        # _ = [t.update({'ipni_id_short': t['fq_id'][24:]}) for t in taxon_list if 'fq_id' in t]

        taxon_dict = {t.id: t.__dict__.copy() for t in taxa}
        _ = [t.pop('_sa_instance_state') for t in taxon_dict.values()]
        _ = [t.update({'ipni_id_short': t['fq_id'][24:]}) for t in taxon_dict.values() if 'fq_id' in t]

        msg = f'Received {len(taxon_dict)} taxa from database.'
        logger.info(msg)
        return {'TaxaDict': taxon_dict,
                'message':           {
                    'type':     'Information',
                    'message': msg,
                    'additionalText': None,
                    'description':    f'Resource: {parse_resource_from_request(request)}'
                    }}, 200

from flask_restful import Resource
import logging
from flask import request
from typing import List

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Taxon
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)


class TaxonResource(Resource):
    @staticmethod
    def get():
        """returns taxa from taxon database table"""
        taxa: List[Taxon] = get_sql_session().query(Taxon).all()

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

    @staticmethod
    def post():
        """save modified custom fields in taxon model"""
        modified_taxa = request.get_json(force=True).get('ModifiedTaxaCollection')
        for taxon_modified in modified_taxa:
            taxon: Taxon = get_sql_session().query(Taxon).filter(Taxon.id == taxon_modified['id']).first()
            if not taxon:
                logger.error(f'Taxon not found: {taxon.name}. Saving canceled.')
                return ({'message': {
                                    'type':           'Error',
                                    'message':        f'Taxon not found: {taxon.name}. Saving canceled.',
                                    'description':    f'Filename: Resource: {parse_resource_from_request(request)}'
                            }}), 500

            taxon.custom_notes = taxon_modified['custom_notes']
        get_sql_session().commit()

        logger.info(f'Updated {len(modified_taxa)} taxa in database.')
        return {'message': {
                            'type': 'Information',
                            'message': f'Updated {len(modified_taxa)} taxa in database.',
                            'description': f'Resource: {parse_resource_from_request(request)}'
                            },
                'resource': 'TaxonResource'
                }, 200

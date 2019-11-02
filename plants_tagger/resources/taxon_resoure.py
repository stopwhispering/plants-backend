from flask_restful import Resource
import logging
from flask import request
from typing import List

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Taxon, object_as_dict
from flask_2_ui5_py import get_message, throw_exception

from plants_tagger.models.update_traits import update_traits

logger = logging.getLogger(__name__)


class TaxonResource(Resource):
    @staticmethod
    def get():
        """returns taxa from taxon database table"""
        taxa: List[Taxon] = get_sql_session().query(Taxon).all()

        # taxon_dict = {t.id: t.__dict__.copy() for t in taxa}
        # _ = [t.pop('_sa_instance_state') for t in taxon_dict.values()]
        # _ = [t.update({'ipni_id_short': t['fq_id'][24:]}) for t in taxon_dict.values() if 'fq_id' in t]
        taxon_dict = {}
        for taxon in taxa:
            taxon_dict[taxon.id] = object_as_dict(taxon)
            if taxon.fq_id:
                taxon_dict[taxon.id]['ipni_id_short'] = taxon.fq_id[24:]
            if taxon.taxon_to_trait_associations:

                # build a dict of trait categories
                categories = {}
                for link in taxon.taxon_to_trait_associations:
                    if link.trait.trait_category.id not in categories:
                        categories[link.trait.trait_category.id] = {
                            'id': link.trait.trait_category.id,
                            'category_name': link.trait.trait_category.category_name,
                            'sort_flag': link.trait.trait_category.sort_flag,
                            'traits': []
                            }
                    categories[link.trait.trait_category.id]['traits'].append({
                                'id':       link.trait.id,
                                'trait':    link.trait.trait,
                                'observed': link.observed
                                })

                # ui5 frontend requires a list for the json model
                taxon_dict[taxon.id]['trait_categories'] = list(categories.values())

        message = f'Received {len(taxon_dict)} taxa from database.'
        logger.info(message)
        return {'TaxaDict': taxon_dict,
                'message': get_message(message)
                }, 200

    @staticmethod
    def post():
        """two things can be changed in the taxon model, and these are modified in db here:
            - modified custom fields
            - traits"""
        modified_taxa = request.get_json(force=True).get('ModifiedTaxaCollection')
        for taxon_modified in modified_taxa:
            taxon: Taxon = get_sql_session().query(Taxon).filter(Taxon.id == taxon_modified['id']).first()
            if not taxon:
                logger.error(f'Taxon not found: {taxon.name}. Saving canceled.')
                throw_exception(f'Taxon not found: {taxon.name}. Saving canceled.')

            taxon.custom_notes = taxon_modified['custom_notes']
            update_traits(taxon, taxon_modified['trait_categories'])
        get_sql_session().commit()

        logger.info(f'Updated {len(modified_taxa)} taxa in database.')
        return {'resource': 'TaxonResource',
                'message': get_message(f'Updated {len(modified_taxa)} taxa in database.')
                }, 200

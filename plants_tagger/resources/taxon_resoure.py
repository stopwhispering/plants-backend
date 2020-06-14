from flask_restful import Resource
import logging
from flask import request
from typing import List

from plants_tagger import config
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.services.image_services import get_thumbnail_relative_path_for_relative_path
from plants_tagger.util.orm_utils import object_as_dict
from plants_tagger.models.taxon_models import Taxon
from plants_tagger.models.image_models import Image, ImageToTaxonAssociation
from flask_2_ui5_py import get_message, throw_exception

from plants_tagger.services.trait_services import update_traits

logger = logging.getLogger(__name__)


class TaxonResource(Resource):
    @staticmethod
    def get():
        """returns taxa from taxon database table"""
        taxa: List[Taxon] = get_sql_session().query(Taxon).all()
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
                                # 'observed': link.observed,
                                'status': link.status
                                })

                # ui5 frontend requires a list for the json model
                taxon_dict[taxon.id]['trait_categories'] = list(categories.values())

            # images
            taxon_dict[taxon.id]['images'] = []
            if taxon.images:
                for link_obj in taxon.image_to_taxon_associations:
                    image_obj = link_obj.image
                    path_small = get_thumbnail_relative_path_for_relative_path(image_obj.relative_path,
                                                                               size=config.size_thumbnail_image)
                    taxon_dict[taxon.id]['images'].append({'id':           image_obj.id,
                                                           'url_small':    path_small,
                                                           'url_original': image_obj.relative_path,
                                                           'description':  link_obj.description})

            # distribution codes according to WGSRPD (level 3)
            taxon_dict[taxon.id]['distribution'] = {'native': [],
                                                    'introduced': []}
            for distribution_obj in taxon.distribution:
                if distribution_obj.establishment == 'Native':
                    taxon_dict[taxon.id]['distribution']['native'].append(distribution_obj.tdwg_code)
                elif distribution_obj.establishment == 'Introduced':
                    taxon_dict[taxon.id]['distribution']['introduced'].append(distribution_obj.tdwg_code)

        message = f'Received {len(taxon_dict)} taxa from database.'
        logger.info(message)
        return {'TaxaDict': taxon_dict,
                'message': get_message(message)
                }, 200

    @staticmethod
    def post():
        """two things can be changed in the taxon model, and these are modified in extensions here:
            - modified custom fields
            - traits"""
        modified_taxa = request.get_json(force=True).get('ModifiedTaxaCollection')
        for taxon_modified in modified_taxa:
            taxon: Taxon = get_sql_session().query(Taxon).filter(Taxon.id == taxon_modified['id']).first()
            if not taxon:
                logger.error(f'Taxon not found: {taxon.name}. Saving canceled.')
                throw_exception(f'Taxon not found: {taxon.name}. Saving canceled.')

            taxon.custom_notes = taxon_modified['custom_notes']
            update_traits(taxon, taxon_modified.get('trait_categories'))

            # changes to images attached to the taxon
            # deleted images
            url_originals_saved = [image.get('url_original') for image in taxon_modified.get('images')] if \
                taxon_modified.get('images') else []
            for image_obj in taxon.images:
                if image_obj.relative_path not in url_originals_saved:
                    # don't delete image object, but only the association (image might be assigned to other events)
                    get_sql_session().delete([link for link in taxon.image_to_taxon_associations if
                                              link.image.relative_path == image_obj.relative_path][0])

            # newly assigned images
            if taxon_modified.get('images'):
                for image in taxon_modified.get('images'):
                    image_obj = get_sql_session().query(Image).filter(Image.relative_path == image.get(
                            'url_original')).first()

                    # not assigned to any event, yet
                    if not image_obj:
                        image_obj = Image(relative_path=image.get('url_original'))
                        get_sql_session().add(image_obj)
                        get_sql_session().flush()  # required to obtain id

                    # update link table including the image description
                    current_taxon_to_image_link = [t for t in taxon.image_to_taxon_associations if t.image == image_obj]

                    # insert link
                    if not current_taxon_to_image_link:
                        link = ImageToTaxonAssociation(image_id=image_obj.id,
                                                       taxon_id=taxon.id,
                                                       description=image.get('description'))
                        get_sql_session().add(link)
                        logger.info(f'Image {image_obj.relative_path} assigned to taxon {taxon.name}')

                    # update description
                    elif current_taxon_to_image_link[0].description != image.get('description'):
                        current_taxon_to_image_link[0].description = image.get('description')
                        logger.info(f'Update description of link between image {image_obj.relative_path} and taxon'
                                    f' {taxon.name}')

        get_sql_session().commit()

        logger.info(f'Updated {len(modified_taxa)} taxa in database.')
        return {'resource': 'TaxonResource',
                'message': get_message(f'Updated {len(modified_taxa)} taxa in database.')
                }, 200

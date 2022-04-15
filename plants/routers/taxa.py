from pathlib import PurePath

from fastapi import APIRouter, Depends
import logging
from typing import List
from sqlalchemy.orm import Session
from starlette.requests import Request

from plants.util.ui_utils import throw_exception, get_message
from plants import config
from plants.util.path_utils import get_thumbnail_relative_path_for_relative_path
from plants.models.taxon_models import Taxon
from plants.dependencies import get_db
from plants.models.image_models import ImageToTaxonAssociation, Image
from plants.services.trait_services import update_traits
from plants.validation.message_validation import PConfirmation
from plants.validation.taxon_validation import PResultsGetTaxa, PModifiedTaxa

logger = logging.getLogger(__name__)

router = APIRouter(
        prefix="/taxa",
        tags=["taxa"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/", response_model=PResultsGetTaxa)
async def get_taxa(
        db: Session = Depends(get_db)
        ):
    """returns taxa from taxon database table"""
    taxa: List[Taxon] = db.query(Taxon).all()
    taxon_dict = {}
    for taxon in taxa:
        taxon_dict[taxon.id] = taxon.as_dict()
        if taxon.taxon_to_trait_associations:

            # build a dict of trait categories
            categories = {}
            for link in taxon.taxon_to_trait_associations:
                if link.trait.trait_category.id not in categories:
                    categories[link.trait.trait_category.id] = {
                        'id':            link.trait.trait_category.id,
                        'category_name': link.trait.trait_category.category_name,
                        'sort_flag':     link.trait.trait_category.sort_flag,
                        'traits':        []
                        }
                categories[link.trait.trait_category.id]['traits'].append({
                    'id':     link.trait.id,
                    'trait':  link.trait.trait,
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
                path_small = get_thumbnail_relative_path_for_relative_path(PurePath(image_obj.relative_path),
                                                                           size=config.size_thumbnail_image)
                taxon_dict[taxon.id]['images'].append({'id':            image_obj.id,
                                                       'relative_path_thumb':    path_small,
                                                       'relative_path': image_obj.relative_path,
                                                       'description':   link_obj.description})

        # distribution codes according to WGSRPD (level 3)
        taxon_dict[taxon.id]['distribution'] = {'native':     [],
                                                'introduced': []}
        for distribution_obj in taxon.distribution:
            if distribution_obj.establishment == 'Native':
                taxon_dict[taxon.id]['distribution']['native'].append(distribution_obj.tdwg_code)
            elif distribution_obj.establishment == 'Introduced':
                taxon_dict[taxon.id]['distribution']['introduced'].append(distribution_obj.tdwg_code)

        # occurence images
        taxon_dict[taxon.id]['occurrenceImages'] = [o.as_dict() for o in taxon.occurence_images]

    logger.info(message := f'Received {len(taxon_dict)} taxa from database.')
    results = {'action':   'Get taxa',
               'resource': 'TaxonResource',
               'message':  get_message(message),
               'TaxaDict': taxon_dict}

    # snake_case is converted to camelCase and date is converted to isoformat
    # results = PResultsGetTaxa(**results).dict(by_alias=True)
    return results


@router.put("/", response_model=PConfirmation)
async def update_taxa(request: Request, modified_taxa: PModifiedTaxa, db: Session = Depends(get_db)):
    """two things can be changed in the taxon model, and these are modified in extensions here:
        - modified custom fields
        - traits"""
    modified_taxa = modified_taxa.ModifiedTaxaCollection

    for taxon_modified in modified_taxa:
        taxon: Taxon = db.query(Taxon).filter(Taxon.id == taxon_modified.id).first()
        if not taxon:
            logger.error(f'Taxon not found: {taxon.name}. Saving canceled.')
            throw_exception(f'Taxon not found: {taxon.name}. Saving canceled.', request=request)

        taxon.custom_notes = taxon_modified.custom_notes
        update_traits(taxon, taxon_modified.trait_categories, db)

        # changes to images attached to the taxon
        # deleted images
        # path_originals_saved = [image.path_original for image in taxon_modified.images] if \
        path_originals_saved = [image.relative_path for image in taxon_modified.images] if \
            taxon_modified.images else []
        for image_obj in taxon.images:
            if image_obj.relative_path not in path_originals_saved:
                # don't delete photo_file object, but only the association
                # (photo_file might be assigned to other events)
                db.delete([link for link in taxon.image_to_taxon_associations if
                           link.image.relative_path == image_obj.relative_path][0])

        # newly assigned images
        if taxon_modified.images:
            for image in taxon_modified.images:
                # image_obj = db.query(Image).filter(Image.relative_path == image.path_original.as_posix()).first()
                image_obj = db.query(Image).filter(Image.relative_path == image.relative_path.as_posix()).first()

                # not assigned to any event, yet
                if not image_obj:
                    raise ValueError(f'Image not in db: {image.relative_path.as_posix()}')

                # update link table including the photo_file description
                current_taxon_to_image_link = [t for t in taxon.image_to_taxon_associations if t.image == image_obj]

                # insert link
                if not current_taxon_to_image_link:
                    link = ImageToTaxonAssociation(image_id=image_obj.id,
                                                   taxon_id=taxon.id,
                                                   description=image.description)
                    db.add(link)
                    logger.info(f'Image {image_obj.relative_path} assigned to taxon {taxon.name}')

                # update description
                elif current_taxon_to_image_link[0].description != image.description:
                    current_taxon_to_image_link[0].description = image.description
                    logger.info(f'Update description of link between image {image_obj.relative_path} and taxon'
                                f' {taxon.name}')

    db.commit()

    results = {'action':   'Save taxa',
               'resource': 'TaxonResource',
               'message':  get_message(f'Updated {len(modified_taxa)} taxa in database.')
               }

    logger.info(f'Updated {len(modified_taxa)} taxa in database.')
    return results

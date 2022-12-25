import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, subqueryload
from starlette.requests import Request

# from plants.models.trait_models import TaxonToTraitAssociation
from plants.util.ui_utils import throw_exception, get_message
from plants.models.taxon_models import Taxon
from plants.dependencies import get_db
from plants.models.image_models import ImageToTaxonAssociation, Image
# from plants.services.trait_services import update_traits
from plants.validation.message_validation import BConfirmation
from plants.validation.taxon_validation import BResultsGetTaxa, FModifiedTaxa, FBTaxon, FBTaxonImage

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/taxa",
    tags=["taxa"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=BResultsGetTaxa)
async def get_taxa(db: Session = Depends(get_db)):
    """returns taxa from taxon database table"""
    taxa: list[Taxon] = db.query(Taxon).options(  # noqa
        subqueryload(Taxon.distribution),
        subqueryload(Taxon.occurrence_images),
        subqueryload(Taxon.images),
        # subqueryload(Taxon.plants),  # not required
        # subqueryload(Taxon.property_values_taxon),  # not required
        subqueryload(Taxon.image_to_taxon_associations)
        .subqueryload(ImageToTaxonAssociation.image),
    ).all()
    taxon_dict = {}
    for taxon in taxa:
        taxon_dict[taxon.id] = taxon.as_dict()

        # images
        taxon_dict[taxon.id]['images'] = []
        if taxon.images:
            for link_obj in taxon.image_to_taxon_associations:
                image_obj: Image = link_obj.image
                taxon_dict[taxon.id]['images'].append({'id': image_obj.id,
                                                       'filename': image_obj.filename,
                                                       'description': link_obj.description})

        # distribution codes according to WGSRPD (level 3)
        taxon_dict[taxon.id]['distribution'] = {'native': [],
                                                'introduced': []}
        for distribution_obj in taxon.distribution:
            if distribution_obj.establishment == 'Native':
                taxon_dict[taxon.id]['distribution']['native'].append(distribution_obj.tdwg_code)
            elif distribution_obj.establishment == 'Introduced':
                taxon_dict[taxon.id]['distribution']['introduced'].append(distribution_obj.tdwg_code)

        # occurence images
        taxon_dict[taxon.id]['occurrenceImages'] = [o.as_dict() for o in taxon.occurrence_images]

    logger.info(message := f'Received {len(taxon_dict)} taxa from database.')
    results = {'action': 'Get taxa',
               'resource': 'TaxonResource',
               'message': get_message(message),
               'TaxaDict': taxon_dict}

    # snake_case is converted to camelCase and date is converted to isoformat
    # results = PResultsGetTaxa(**results).dict(by_alias=True)
    return results


@router.put("/", response_model=BConfirmation)
async def update_taxa(request: Request, modified_taxa: FModifiedTaxa, db: Session = Depends(get_db)):
    """two things can be changed in the taxon model, and these are modified in extensions here:
        - modified custom fields
        - traits"""
    modified_taxa = modified_taxa.ModifiedTaxaCollection

    for taxon_modified in modified_taxa:
        taxon_modified: FBTaxon
        taxon: Taxon = db.query(Taxon).filter(Taxon.id == taxon_modified.id).first()
        if not taxon:
            logger.error(f'Taxon not found: {taxon.name}. Saving canceled.')
            throw_exception(f'Taxon not found: {taxon.name}. Saving canceled.', request=request)

        taxon.custom_notes = taxon_modified.custom_notes
        # update_traits(taxon, taxon_modified.trait_categories, db)  # todo still required?

        # changes to images attached to the taxon
        # deleted images
        # path_originals_saved = [image.path_original for image in taxon_modified.images] if \
        image: FBTaxonImage
        filenames_saved = ([image.filename for image in taxon_modified.images]
                           if taxon_modified.images else [])
        for image_obj in taxon.images:
            image_obj: Image
            if image_obj.filename not in filenames_saved:
                # don't delete photo_file object, but only the association
                # (photo_file might be assigned to other events)
                link: ImageToTaxonAssociation
                db.delete([link for link in taxon.image_to_taxon_associations if
                           link.image.relative_path == image_obj.relative_path][0])

        # newly assigned images
        if taxon_modified.images:
            for image in taxon_modified.images:
                # image_obj = db.query(Image).filter(Image.relative_path == image.relative_path.as_posix()).first()
                image_obj = Image.get_image_by_filename(filename=image.filename, db=db)
                # if not image_obj:
                # if not Image.exists(filename=image.filename, db=db):
                #     # not assigned to any event, yet
                #     raise ValueError(f'Image not in db: {image.relative_path.as_posix()}')

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

    results = {'action': 'Save taxa',
               'resource': 'TaxonResource',
               'message': get_message(f'Updated {len(modified_taxa)} taxa in database.')
               }

    logger.info(f'Updated {len(modified_taxa)} taxa in database.')
    return results

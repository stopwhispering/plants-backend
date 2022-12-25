import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, subqueryload
from starlette.requests import Request

from plants.services.taxon_services import get_taxon_for_api_by_taxon_id
# from plants.models.trait_models import TaxonToTraitAssociation
from plants.util.ui_utils import throw_exception, get_message
from plants.models.taxon_models import Taxon
from plants.dependencies import get_db
from plants.models.image_models import ImageToTaxonAssociation, Image
# from plants.services.trait_services import update_traits
from plants.validation.message_validation import BConfirmation
from plants.validation.taxon_validation import FModifiedTaxa, FBTaxon, FBTaxonImage, BResultsGetTaxon

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/taxa",
    tags=["taxa"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{taxon_id}", response_model=BResultsGetTaxon)
async def get_taxon(taxon_id: int, db: Session = Depends(get_db)):
    """
    returns taxon with requested taxon_id
    """
    taxon: dict = get_taxon_for_api_by_taxon_id(taxon_id=taxon_id, db=db)
    results = BResultsGetTaxon.parse_obj({'action': 'Get taxa',
                                          'message': get_message(f'Read taxon {taxon_id} from database.'),
                                          'taxon': taxon})

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

        # changes to images attached to the taxon
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

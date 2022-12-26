import logging

from sqlalchemy.orm import Session

from plants.util.ui_utils import throw_exception
from plants.models.taxon_models import Taxon
from plants.models.image_models import ImageToTaxonAssociation, Image
from plants.validation.taxon_validation import FTaxon, FTaxonImage

logger = logging.getLogger(__name__)


def modify_taxon(taxon_modified: FTaxon, db: Session):
    taxon: Taxon = db.query(Taxon).filter(Taxon.id == taxon_modified.id).first()
    if not taxon:
        logger.error(f'Taxon not found: {taxon.name}. Saving canceled.')
        throw_exception(f'Taxon not found: {taxon.name}. Saving canceled.')

    taxon.custom_notes = taxon_modified.custom_notes

    # changes to images attached to the taxon
    image: FTaxonImage
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
            image_obj = Image.get_image_by_id(id_=image.id, db=db)
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
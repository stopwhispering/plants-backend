from sqlalchemy.orm import Session

from plants.models.image_models import Image
from plants.models.taxon_models import Taxon
from plants.validation.taxon_validation import FBTaxon, FBTaxonOccurrenceImage


def get_taxon_for_api_by_taxon_id(taxon_id: int, db: Session) -> dict:
    taxon: Taxon = db.query(Taxon).filter(Taxon.id == taxon_id).first()
    taxon_dict = taxon.as_dict()

    # images
    taxon_dict['images'] = []
    if taxon.images:
        for link_obj in taxon.image_to_taxon_associations:
            image_obj: Image = link_obj.image
            taxon_dict['images'].append({'id': image_obj.id,
                                         'filename': image_obj.filename,
                                         'description': link_obj.description})

    # distribution codes according to WGSRPD (level 3)
    taxon_dict['distribution'] = {'native': [],
                                  'introduced': []}
    for distribution_obj in taxon.distribution:
        if distribution_obj.establishment == 'Native':
            taxon_dict['distribution']['native'].append(distribution_obj.tdwg_code)
        elif distribution_obj.establishment == 'Introduced':
            taxon_dict['distribution']['introduced'].append(distribution_obj.tdwg_code)

    # occurence images
    taxon_dict['occurrenceImages'] = [o.as_dict() for o in taxon.occurrence_images]
    return taxon_dict
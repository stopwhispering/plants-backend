import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from plants.services.taxon_services import modify_taxon
from plants.util.ui_utils import get_message
from plants.models.taxon_models import Taxon
from plants.dependencies import get_db
from plants.validation.message_validation import BSaveConfirmation, FBMajorResource
from plants.validation.taxon_validation import FModifiedTaxa, BResultsGetTaxon

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/taxa",
    tags=["taxa"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{taxon_id}", response_model=BResultsGetTaxon)
async def get_taxon(taxon_id: int, db: Session = Depends(get_db)):
    """
    returns taxon for requested taxon_id
    """
    taxon: Taxon = Taxon.get_taxon_by_taxon_id(taxon_id=taxon_id, db=db)
    results = {'action': 'Get taxa',
               'message': get_message(f'Read taxon {taxon_id} from database.'),
               'taxon': taxon}
    return results


@router.put("/", response_model=BSaveConfirmation)
async def update_taxa(modified_taxa: FModifiedTaxa, db: Session = Depends(get_db)):
    """
    update 1..n taxa in database
    """
    modified_taxa = modified_taxa.ModifiedTaxaCollection
    for taxon_modified in modified_taxa:
        modify_taxon(taxon_modified=taxon_modified, db=db)

    db.commit()

    results = {'action': 'Save taxa',
               'resource': FBMajorResource.TAXON,
               'message': get_message(msg := f'Updated {len(modified_taxa)} taxa in database.')
               }
    logger.info(msg)
    return results

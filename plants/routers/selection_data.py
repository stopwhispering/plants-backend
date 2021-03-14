from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session

from plants.util.ui_utils import make_list_items_json_serializable, get_message
from plants.dependencies import get_db
from plants.validation.selection_validation import PResultsSelection
from plants.services.selection_services import build_taxon_tree

logger = logging.getLogger(__name__)

router = APIRouter(
        prefix="/selection_data",
        tags=["selection_data"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/", response_model=PResultsSelection)
async def get_selection_data(db: Session = Depends(get_db)):
    """build & return taxon tree for advanced filtering"""
    taxon_tree = build_taxon_tree(db)
    make_list_items_json_serializable(taxon_tree)

    results = {'action':    'Get taxon tree',
               'resource':  'SelectionResource',
               'message':   get_message(f"Loaded selection data."),
               'Selection': {'TaxonTree': taxon_tree}}

    return results

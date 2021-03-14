from fastapi import APIRouter, Depends
import logging
from pydantic.error_wrappers import ValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request

from plants.util.ui_utils import throw_exception, make_list_items_json_serializable, get_message
from plants.dependencies import get_db
from plants.validation.selection_validation import PResultsSelection
from plants.services.selection_services import build_taxon_tree

logger = logging.getLogger(__name__)

router = APIRouter(
        prefix="/selection_data",
        tags=["selection_data"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/")
async def get_selection_data(request: Request, db: Session = Depends(get_db)):
    """build & return taxon tree for advanced filtering"""
    taxon_tree = build_taxon_tree(db)
    make_list_items_json_serializable(taxon_tree)

    results = {'action':    'Get taxon tree',
               'resource':  'SelectionResource',
               'message':   get_message(f"Loaded selection data."),
               'Selection': {'TaxonTree': taxon_tree}}

    # evaluate output
    try:
        PResultsSelection(**results)
    except ValidationError as err:
        throw_exception(str(err), request=request)

    return results

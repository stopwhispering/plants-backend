from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session
from starlette.requests import Request

from plants.modules.plant.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.shared.proposal_schemas import FProposalEntity, BResultsProposals, BResultsSelection
from plants.shared.proposal_services import build_taxon_tree
from plants.shared.api_utils import make_list_items_json_serializable
from plants.shared.message_services import throw_exception, get_message
from plants.dependencies import get_db, get_image_dal

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["proposals", "selection_data"],
    responses={404: {"description": "Not found"}},
)


@router.get("/proposals/{entity_id}", response_model=BResultsProposals)
def get_proposals(request: Request, entity_id: FProposalEntity, db: Session = Depends(get_db),
                  image_dal: ImageDAL = Depends(get_image_dal) ):
    """returns proposals for selection tables"""

    results = {}

    if entity_id == FProposalEntity.NURSERY:
        # get distinct nurseries/sources, sorted by last update
        nurseries_tuples = (db.query(Plant.nursery_source)
                            # .order_by(Plant.last_update.desc())
                            .distinct(Plant.nursery_source)
                            .filter(Plant.nursery_source.isnot(None)).all())
        if not nurseries_tuples:
            results = {'NurseriesSourcesCollection': []}
        else:
            results = {'NurseriesSourcesCollection': [{'name': n[0]} for n in nurseries_tuples]}

    elif entity_id == FProposalEntity.KEYWORD:
        # return collection of all distinct keywords used in images
        # keywords_set = get_distinct_keywords_from_image_files()
        keywords_set = image_dal.get_distinct_image_keywords()
        keywords_collection = [{'keyword': keyword} for keyword in keywords_set]
        results = {'KeywordsCollection': keywords_collection}

    else:
        throw_exception(f'Proposal entity {entity_id} not expected.', request=request)

    results.update({'action': 'Get',
                    'message': get_message(f'Receiving proposal values for entity {entity_id} from backend.')})

    return results


@router.get("/selection_data/", response_model=BResultsSelection)
async def get_selection_data(db: Session = Depends(get_db)):
    """build & return taxon tree for advanced filtering"""
    taxon_tree = build_taxon_tree(db)
    make_list_items_json_serializable(taxon_tree)

    results = {'action':    'Get taxon tree',
               'message':   get_message(f"Loaded selection data."),
               'Selection': {'TaxonTree': taxon_tree}}

    return results

from typing import List
from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session
from starlette.requests import Request

# from plants.constants import TRAIT_CATEGORIES
from plants.models.plant_models import Plant
from plants.services.plants_services import get_distinct_image_keywords
from plants.validation.proposal_validation import FProposalEntity, BResultsProposals
# from plants.models.trait_models import Trait, TraitCategory
from plants.util.ui_utils import throw_exception, get_message
from plants.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/proposals",
    tags=["proposals"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{entity_id}", response_model=BResultsProposals)
def get_proposals(request: Request, entity_id: FProposalEntity, db: Session = Depends(get_db)):
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
        keywords_set = get_distinct_image_keywords(db=db)
        keywords_collection = [{'keyword': keyword} for keyword in keywords_set]
        results = {'KeywordsCollection': keywords_collection}


    else:
        throw_exception(f'Proposal entity {entity_id} not expected.', request=request)

    results.update({'action': 'Get',
                    'message': get_message(f'Receiving proposal values for entity {entity_id} from backend.')})

    return results

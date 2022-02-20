from typing import List
from fastapi import APIRouter, Depends
import logging
from sqlalchemy.orm import Session
from starlette.requests import Request

from plants.constants import TRAIT_CATEGORIES
from plants.models.plant_models import Plant
from plants.validation.proposal_validation import ProposalEntity, PResultsProposals
from plants.services.image_services import get_distinct_keywords_from_image_files
from plants.models.trait_models import Trait, TraitCategory
from plants.util.ui_utils import throw_exception, get_message
from plants.dependencies import get_db

logger = logging.getLogger(__name__)


router = APIRouter(
        prefix="/proposals",
        tags=["proposals"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/{entity_id}", response_model=PResultsProposals)
def get_proposals(request: Request, entity_id: ProposalEntity, db: Session = Depends(get_db)):
    """returns proposals for selection tables"""

    results = {}

    if entity_id == ProposalEntity.NURSERY:
        # get distinct nurseries/sources, sorted by last update
        nurseries_tuples = db.query(Plant.nursery_source) \
            .order_by(Plant.last_update.desc()) \
            .distinct(Plant.nursery_source)\
            .filter(Plant.nursery_source.isnot(None)).all()
        if not nurseries_tuples:
            results = {'NurseriesSourcesCollection': []}
        else:
            results = {'NurseriesSourcesCollection': [{'name': n[0]} for n in nurseries_tuples]}

    elif entity_id == ProposalEntity.KEYWORD:
        # return collection of all distinct keywords used in images
        keywords_set = get_distinct_keywords_from_image_files()
        keywords_collection = [{'keyword': keyword} for keyword in keywords_set]
        results = {'KeywordsCollection': keywords_collection}

    elif entity_id == ProposalEntity.TRAIT_CATEGORY:
        # trait categories
        trait_categories = []
        t: Trait
        for t in TRAIT_CATEGORIES:
            # note: trait categories from config file are created in orm_tables.py if not existing upon start
            trait_category_obj = TraitCategory.get_cat_by_name(t, db, raise_exception=True)
            trait_categories.append(trait_category_obj.as_dict())
        results = {'TraitCategoriesCollection': trait_categories}

        # traits
        traits_query: List[Trait] = db.query(Trait).filter(Trait.trait_category.has(
                TraitCategory.category_name.in_(TRAIT_CATEGORIES)))
        traits = []
        for t in traits_query:
            t_dict = t.as_dict()
            t_dict['trait_category_id'] = t.trait_category_id
            t_dict['trait_category'] = t.trait_category.category_name
            traits.append(t_dict)
        results['TraitsCollection'] = traits

    else:
        throw_exception(f'Proposal entity {entity_id} not expected.', request=request)

    results.update({'action': 'Get',
                    'resource': 'ProposalResource',
                    'message': get_message(f'Receiving proposal values for entity {entity_id} from backend.')})

    return results

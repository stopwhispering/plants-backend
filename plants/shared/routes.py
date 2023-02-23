import logging

from fastapi import APIRouter, Depends
from starlette.requests import Request

from plants.dependencies import get_image_dal, get_plant_dal, get_taxon_dal
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.api_utils import make_list_items_json_serializable
from plants.shared.enums import FProposalEntity
from plants.shared.message_services import get_message, throw_exception
from plants.shared.proposal_schemas import BResultsProposals, BResultsSelection
from plants.shared.proposal_services import build_taxon_tree

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["proposals", "selection_data"],
    responses={404: {"description": "Not found"}},
)


@router.get("/proposals/{entity_id}", response_model=BResultsProposals)
async def get_proposals(request: Request, entity_id: FProposalEntity,
                        image_dal: ImageDAL = Depends(get_image_dal),
                        plant_dal: PlantDAL = Depends(get_plant_dal)):
    """returns proposals for selection tables"""

    results = {}

    if entity_id == FProposalEntity.NURSERY:
        # get distinct nurseries/sources, sorted by last update
        nurseries = await plant_dal.get_distinct_nurseries()
        # nurseries_tuples = (db.query(Plant.nursery_source)
        #                     # .order_by(Plant.last_update.desc())
        #                     .distinct(Plant.nursery_source)
        #                     .filter(Plant.nursery_source.isnot(None)).all())
        # if not nurseries:
        #     results = {'NurseriesSourcesCollection': []}
        # else:
        results = {'NurseriesSourcesCollection': [{'name': n} for n in nurseries]}

    elif entity_id == FProposalEntity.KEYWORD:
        # return collection of all distinct keywords used in images
        # keywords_set = get_distinct_keywords_from_image_files()
        keywords_set = await image_dal.get_distinct_image_keywords()
        keywords_collection = [{'keyword': keyword} for keyword in keywords_set]
        results = {'KeywordsCollection': keywords_collection}

    else:
        throw_exception(f'Proposal entity {entity_id} not expected.', request=request)

    results.update({'action': 'Get',
                    'message': get_message(f'Receiving proposal values for entity {entity_id} from backend.')})

    return results


@router.get("/selection_data/", response_model=BResultsSelection)
async def get_selection_data(taxon_dal: TaxonDAL = Depends(get_taxon_dal),
                             plant_dal: PlantDAL = Depends(get_plant_dal)):
    """build & return taxon tree for advanced filtering"""
    taxon_tree = await build_taxon_tree(taxon_dal=taxon_dal, plant_dal=plant_dal)
    make_list_items_json_serializable(taxon_tree)

    results = {'action': 'Get taxon tree',
               'message': get_message(f"Loaded selection data."),
               'Selection': {'TaxonTree': taxon_tree}}

    return results

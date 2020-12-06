from typing import List

from flask_restful import Resource
import logging

from pydantic.error_wrappers import ValidationError

from plants_tagger.config import TRAIT_CATEGORIES
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.plant_models import Plant
from plants_tagger.validation.proposal_validation import ProposalEntity, PEntityName, PResultsProposals
from plants_tagger.services.image_services import get_distinct_keywords_from_image_files
from plants_tagger.models.trait_models import Trait, TraitCategory
from plants_tagger.models.event_models import Soil, SoilComponent
from flask_2_ui5_py import throw_exception, get_message

logger = logging.getLogger(__name__)


class ProposalResource(Resource):
    @staticmethod
    def get(entity_id):
        """returns proposals for selection tables"""

        # evaluate arguments
        try:
            PEntityName.parse_obj(entity_id)
        except ValidationError as err:
            throw_exception(str(err))

        results = {}
        if entity_id == ProposalEntity.SOIL:
            results = {'SoilsCollection': [],
                       'ComponentsCollection': []}
            # soil mixes
            soils = get_sql_session().query(Soil).all()
            for soil in soils:
                soil_dict = soil.as_dict()
                soil_dict['components'] = [{'component_name': c.soil_component.component_name,
                                            'portion': c.portion} for c in soil.soil_to_component_associations]

                results['SoilsCollection'].append(soil_dict)

            # soil components for new mixes
            components = get_sql_session().query(SoilComponent).all()
            results['ComponentsCollection'] = [{'component_name': c.component_name} for c in components]

        elif entity_id == ProposalEntity.NURSERY:
            # get distinct nurseries/sources, sorted by last update
            nurseries_tuples = get_sql_session().query(Plant.nursery_source) \
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
                trait_category_obj = TraitCategory.get_cat_by_name(t, raise_exception=True)
                trait_categories.append(trait_category_obj.as_dict())
            results = {'TraitCategoriesCollection': trait_categories}

            # traits
            traits_query: List[Trait] = get_sql_session().query(Trait).filter(Trait.trait_category.has(
                    TraitCategory.category_name.in_(TRAIT_CATEGORIES)))
            traits = []
            for t in traits_query:
                t_dict = t.as_dict()
                t_dict['trait_category_id'] = t.trait_category_id
                t_dict['trait_category'] = t.trait_category.category_name
                traits.append(t_dict)
            results['TraitsCollection'] = traits

        else:
            throw_exception(f'Proposal entity {entity_id} not expected.')

        results.update({'action': 'Get',
                        'resource': 'ProposalResource',
                        'message': get_message(f'Receiving proposal values for entity {entity_id} from backend.')})

        # evaluate output
        try:
            PResultsProposals(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

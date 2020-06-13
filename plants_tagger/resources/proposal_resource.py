from flask_restful import Resource
import logging

from plants_tagger.config import TRAIT_CATEGORIES
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.plant_models import Plant
from plants_tagger.services.files import get_distinct_keywords_from_image_files
from plants_tagger.util.rest import object_as_dict
from plants_tagger.models.trait_models import Trait, TraitCategory
from plants_tagger.models.event_models import Soil, SoilComponent
from flask_2_ui5_py import throw_exception, get_message

logger = logging.getLogger(__name__)


class ProposalResource(Resource):
    @staticmethod
    def get(entity_id):
        """returns proposals for selection tables"""
        results = []
        if entity_id == 'SoilProposals':
            results = {'SoilsCollection': [],
                       'ComponentsCollection': []}
            # soil mixes
            soils = get_sql_session().query(Soil).all()
            for soil in soils:
                soil_dict = object_as_dict(soil)
                soil_dict['components'] = [{'component_name': c.soil_component.component_name,
                                            'portion': c.portion} for c in soil.soil_to_component_associations]

                results['SoilsCollection'].append(soil_dict)

            # soil components for new mixes
            components = get_sql_session().query(SoilComponent).all()
            results['ComponentsCollection'] = [{'component_name': c.component_name} for c in components]

        elif entity_id == 'NurserySourceProposals':
            # get distinct nurseries/sources, sorted by last update
            nurseries_tuples = get_sql_session().query(Plant.nursery_source) \
                .order_by(Plant.last_update.desc()) \
                .distinct(Plant.nursery_source)\
                .filter(Plant.nursery_source.isnot(None)).all()
            if not nurseries_tuples:
                results = {'NurseriesSourcesCollection': []}
            else:
                results = {'NurseriesSourcesCollection': [{'name': n[0]} for n in nurseries_tuples]}

        elif entity_id == 'KeywordProposals':
            # return collection of all distinct keywords used in images
            keywords_set = get_distinct_keywords_from_image_files()
            keywords_collection = [{'keyword': keyword} for keyword in keywords_set]
            results = {'KeywordsCollection': keywords_collection}

        elif entity_id == 'TraitCategoryProposals':
            # trait categories
            trait_categories = []
            t: Trait
            for t in TRAIT_CATEGORIES:
                # note: trait categories from config file are created in orm_tables.py if not existing upon start
                trait_category_obj = get_sql_session().query(TraitCategory).filter(TraitCategory.category_name ==
                                                                                   t).first()
                trait_categories.append(object_as_dict(trait_category_obj))
            results = {'TraitCategoriesCollection': trait_categories}

            # traits
            traits_obj = get_sql_session().query(Trait).all()
            traits_obj = [t for t in traits_obj if t.trait_category.category_name in TRAIT_CATEGORIES]
            traits = []
            for t in traits_obj:
                t_dict = object_as_dict(t)
                t_dict['trait_category_id'] = t.trait_category_id
                t_dict['trait_category'] = t.trait_category.category_name
                traits.append(t_dict)
            results['TraitsCollection'] = traits

        else:
            throw_exception(f'Proposal entity {entity_id} not expected.')

        results['message'] = get_message(f'Loaded proposal values for entity {entity_id} from backend.')
        return results, 200

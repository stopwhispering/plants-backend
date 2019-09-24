from flask_restful import Resource
import logging

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Soil, SoilComponent, object_as_dict
from plants_tagger.util.json_helper import throw_exception, get_message

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

        else:
            throw_exception(f'Proposal entity {entity_id} not expected.')

        results['message'] = get_message(f'Loaded proposal values for entity {entity_id} from backend.')
        return results, 200

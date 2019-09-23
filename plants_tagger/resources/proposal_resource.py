from flask_restful import Resource
import logging
from flask import request
from typing import List

from plants_tagger.models import get_sql_session
from plants_tagger.models.orm_tables import Taxon, Event, Plant, Pot, Soil, SoilComponent, SoilToComponentAssociation, \
    object_as_dict
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)


class ProposalResource(Resource):
    @staticmethod
    def get(entity_id):
        """returns proposals for selection tables"""
        # if request.args['entity'] == 'SoilsCollection':
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
            # todo message entity not found
            return {'error': 'error'}
        return results, 200
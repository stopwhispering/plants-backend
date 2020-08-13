from flask_restful import Resource
import logging

from flask_2_ui5_py import make_list_items_json_serializable, get_message, throw_exception

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.property_models import PropertyCategory

logger = logging.getLogger(__name__)


class PropertyNameResource(Resource):

    @staticmethod
    def get():
        categories = get_sql_session().query(PropertyCategory).all()
        results = {}
        for cat in categories:
            results[cat.category_name] = [{'property_name': p.property_name,
                                           'property_name_id': p.id,
                                           'countPlants': len(p.property_values)
                                           } for p in cat.property_names]

        # make_list_items_json_serializable(categories)

        return {
            'propertiesAvailablePerCategory': results,
            'message':             get_message(f"Loaded Property Names from database.")
            }, 200

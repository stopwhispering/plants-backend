from flask_restful import Resource
import logging

from flask_2_ui5_py import get_message, throw_exception
from pydantic.error_wrappers import ValidationError

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.property_models import PropertyCategory
from plants_tagger.models.validation.property_validation import PResultsPropertyNames

logger = logging.getLogger(__name__)


class PropertyNameResource(Resource):

    @staticmethod
    def get():
        category_obj = get_sql_session().query(PropertyCategory).all()
        categories = {}
        for cat in category_obj:
            categories[cat.category_name] = [{'property_name':    p.property_name,
                                              'property_name_id': p.id,
                                              'countPlants':      len(p.property_values)
                                              } for p in cat.property_names]

        results = {
            'action':                         'Get',
            'resource':                       'PropertyNameResource',
            'propertiesAvailablePerCategory': categories,
            'message':                        get_message(f"Receiving Property Names from database.")
            }

        # evaluate output
        try:
            PResultsPropertyNames(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

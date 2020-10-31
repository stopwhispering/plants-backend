from flask_restful import Resource
import logging
import json
from flask import request

from flask_2_ui5_py import make_list_items_json_serializable, get_message, throw_exception
from pydantic.error_wrappers import ValidationError

from plants_tagger.validation.message_validation import PConfirmation
from plants_tagger.validation.plant_validation import PPlantIdOptional
from plants_tagger.validation.property_validation import PResultsPropertiesForPlant, PPropertiesModifiedPlant, \
    PPropertiesModifiedTaxon
from plants_tagger.services.property_services import SaveProperties, LoadProperties, SavePropertiesTaxa

logger = logging.getLogger(__name__)


class PropertyTaxaResource(Resource):
    """taxon properties; note: there's no get method for taxon properties; they are read with the plant's
    properties"""

    @staticmethod
    def post():
        """save taxon properties"""
        data = json.loads(request.get_data())

        # evaluate arguments
        try:
            PPropertiesModifiedTaxon(**data)
        except ValidationError as err:
            throw_exception(str(err))

        SavePropertiesTaxa().save_properties(properties_modified=data.get('modifiedPropertiesTaxa'))
        results = {'action':   'Update',
                   'resource': 'PropertyTaxaResource',
                   'message':  get_message(f'Updated properties for taxa in database.')
                   }

        # evaluate output
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200  # required for closing busy dialog when saving


class PropertyResource(Resource):
    """plant properties"""

    @staticmethod
    def post():
        """save plant properties"""
        data = json.loads(request.get_data())

        # evaluate arguments
        try:
            PPropertiesModifiedPlant(**data)
        except ValidationError as err:
            throw_exception(str(err))

        SaveProperties().save_properties(data.get('modifiedPropertiesPlants'))
        results = {'action':   'Update',
                   'resource': 'PropertyResource',
                   'message':  get_message(f'Updated properties in database.')
                   }

        # evaluate output
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200  # required for closing busy dialog when saving

    @staticmethod
    def get(plant_id):
        """reads a plant's property values from db; plus it's taxon's property values"""
        if not plant_id:
            throw_exception('Plant id required for Property GET requests')
        if plant_id == 'undefined':
            plant_id = None

        # evaluate arguments
        try:
            PPlantIdOptional.parse_obj(plant_id)
        except ValidationError as err:
            throw_exception(str(err))

        load_properties = LoadProperties()
        categories = load_properties.get_properties_for_plant(plant_id)

        categories_taxon = load_properties.get_properties_for_taxon(int(request.args['taxon_id'])) if request.args.get(
                'taxon_id') else []

        make_list_items_json_serializable(categories)
        make_list_items_json_serializable(categories_taxon)

        results = {
            'propertyCollections':      {"categories": categories},
            'plant_id':                 plant_id,
            'propertyCollectionsTaxon': {"categories": categories_taxon},
            'taxon_id':                 request.args.get('taxon_id'),

            'action':                   'Get',
            'resource':                 'PropertyTaxaResource',
            'message':                  get_message(f"Receiving properties for {plant_id} from database.")
            }

        # evaluate output
        try:
            PResultsPropertiesForPlant(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

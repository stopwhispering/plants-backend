from flask_restful import Resource
import logging
import json
from flask import request

from flask_2_ui5_py import make_list_items_json_serializable, get_message, throw_exception
from plants_tagger.services.property_services import SaveProperties, LoadProperties, SavePropertiesTaxa

logger = logging.getLogger(__name__)


class PropertyTaxaResource(Resource):
    """saving taxon properties; note: there's no get method for taxon properties; they are read with the plant's
    properties"""
    @staticmethod
    def post():
        if not request.get_data():
            throw_exception('Bad request..')
        # modified_properties_plants = json.loads(request.get_data()).get('modifiedPropertiesPlants')
        modified_properties_taxa = json.loads(request.get_data()).get('modifiedPropertiesTaxa')
        SavePropertiesTaxa().save_properties(properties_modified=modified_properties_taxa)
        return {'resource': 'PropertyTaxaResource',
                'message':  get_message(f'Updated properties for taxa in database.')
                }, 200  # required for closing busy dialog when saving


class PropertyResource(Resource):

    @staticmethod
    def post():
        if not request.get_data():
            throw_exception('Bad request..')
        modified_properties_plants = json.loads(request.get_data()).get('modifiedPropertiesPlants')
        # modified_properties_taxa = json.loads(request.get_data()).get('modifiedPropertiesTaxa')
        if not modified_properties_plants:
            throw_exception('No property supplied to modify.')

        SaveProperties().save_properties(modified_properties_plants)
        return {'resource': 'PropertyResource',
                'message':  get_message(f'Updated properties in database.')
                }, 200  # required for closing busy dialog when saving

    @staticmethod
    def get(plant_id):
        """reads a plant's property values from db; plus it's taxon's property values"""
        if not plant_id:
            throw_exception('Plant id required for Property GET requests')

        load_properties = LoadProperties()
        categories = load_properties.get_properties_for_plant(plant_id)

        categories_taxon = load_properties.get_properties_for_taxon(int(request.args['taxon_id'])) if request.args.get(
                'taxon_id') else []

        make_list_items_json_serializable(categories)
        make_list_items_json_serializable(categories_taxon)

        return {
                   'propertyCollections':      {"categories": categories},
                   'plant_id': plant_id,
                   'propertyCollectionsTaxon': {"categories": categories_taxon},
                   'taxon_id': request.args.get('taxon_id'),
                   'message':                  get_message(f"Loaded properties from database.")
                   }, 200

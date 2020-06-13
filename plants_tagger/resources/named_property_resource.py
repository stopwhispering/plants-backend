from flask_restful import Resource
import logging
import json
from flask import request

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.services.properties import get_properties_for_plant_by_category, get_properties_for_taxon_by_category
from flask_2_ui5_py import make_list_items_json_serializable, get_message, throw_exception, \
    MessageType

from plants_tagger.models.taxon_models import Taxon
from plants_tagger.models.plant_models import Plant
from plants_tagger.models.trait_models import TraitCategory
from plants_tagger.models.property_models import PropertyName, PropertyValueTaxon, PropertyValuePlant

logger = logging.getLogger(__name__)


class PropertyResource(Resource):

    @staticmethod
    def post():
        if not request.get_data():
            throw_exception('Bad request..')
        modified = json.loads(request.get_data()).get('propertiesModified')
        if not modified:
            throw_exception('No property supplied to modify.')

        new_list = []
        for mod in modified:

            cat_obj = get_sql_session().query(TraitCategory).filter(TraitCategory.id == mod.get('categoryId')).first()
            if not cat_obj:
                cat_obj = get_sql_session().query(TraitCategory).filter(
                        TraitCategory.category_name == mod.get('category')).first()
                if not cat_obj:
                    cat_obj = TraitCategory(category_name=mod['category'])
                    new_list.append(cat_obj)

            name_obj = get_sql_session().query(PropertyName).filter(PropertyName.id == mod.get('nameId')).first()
            if not name_obj:
                name_obj = get_sql_session().query(PropertyName).filter(
                        PropertyName.property_name == mod.get('name')).first()
                if not name_obj:
                    name_obj = PropertyName(property_name=mod.get('name'),
                                            property_category=cat_obj)
                    new_list.append(name_obj)

            if mod.get('plantName'):
                plant_obj = get_sql_session().query(Plant).filter(Plant.plant_name == mod['plantName']).first()
                value_obj = get_sql_session().query(PropertyValuePlant).filter(
                        PropertyValuePlant.property_name == name_obj,
                        PropertyValuePlant.plant == plant_obj).first()
                if not value_obj:
                    value_obj = PropertyValuePlant(property_name=name_obj,
                                                   plant=plant_obj)
                    new_list.append(value_obj)
                value_obj.property_value = mod.get('value')
            elif mod.get('taxonId'):
                taxon_obj = get_sql_session().query(Taxon).filter(Taxon.id == mod['taxonId']).first()
                value_obj = get_sql_session().query(PropertyValueTaxon).filter(
                        PropertyValueTaxon.property_name == name_obj,
                        PropertyValueTaxon.taxon_id == taxon_obj.id).first()
                if not value_obj:
                    value_obj = PropertyValueTaxon(property_name=name_obj,
                                                   taxon_id=taxon_obj.id)
                    new_list.append(value_obj)
                value_obj.property_value = mod.get('value')
            else:
                throw_exception('Neither plantName nor taxonId supplied.')

        if new_list:
            get_sql_session().add_all(new_list)
        get_sql_session().commit()

        # todo: delete values if empty
        # todo: return success

    @staticmethod
    def get():
        property_requests_s = request.args.get('propertiesToRequest')
        if not property_requests_s:
            throw_exception(f'No plant or taxon requested.', MessageType.ERROR)
        property_requests = json.loads(property_requests_s)

        # collect properties for supplied plants and taxa
        property_collections = []
        for property_request in property_requests:

            if property_request['type'] == 'Plant':
                property_categories_current_plant = get_properties_for_plant_by_category(property_request['value'])
                if property_categories_current_plant:
                    property_collections.append({'type':                property_request['type'],
                                                 'plant_name':          property_request['value'],
                                                 'property_categories': property_categories_current_plant})

            else:
                property_categories_current_taxon = get_properties_for_taxon_by_category(property_request['value'])
                if property_categories_current_taxon:
                    property_collections.append({'type':                property_request['type'],
                                                 'taxon_id':            property_request['value'],
                                                 'property_categories': property_categories_current_taxon})

        make_list_items_json_serializable(property_collections)
        results = {
            'property_collections': property_collections,
            'message': get_message(f"Loaded properties from database.")
            }

        return results, 200


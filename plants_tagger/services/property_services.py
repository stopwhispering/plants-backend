from typing import List, Dict

from plants_tagger.config import PROPERTY_CATEGORIES
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.plant_models import Plant
from plants_tagger.models.property_models import PropertyValue, PropertyCategory, PropertyName
from plants_tagger.models.taxon_models import Taxon


class MixinShared:
    @staticmethod
    def create_new_property_name(category_id, property_name):
        """returns newly createad property name's id"""
        category_obj = PropertyCategory.get_cat_by_id(category_id, raise_exception=True)
        # make sure it does not already exist
        current_property_names = [p for p in category_obj.property_names if p.property_name == property_name]
        if current_property_names:
            return current_property_names[0].id

        property_name = PropertyName(property_name=property_name, category_id=category_id)
        # we need to add it and flush to get a property name id
        get_sql_session().add(property_name)
        get_sql_session().flush()
        return property_name.id


class LoadProperties:
    @staticmethod
    def _add_empty_categories(categories: List):
        category_names = [c['category_name'] for c in categories]
        for default_category in [p for p in PROPERTY_CATEGORIES if p not in category_names]:
            category_obj = PropertyCategory.get_cat_by_name(default_category)
            categories.append({'category_name': category_obj.category_name,
                               'category_id':   category_obj.id,
                               'sort':          category_obj.sort,
                               'properties':    []})

    @staticmethod
    def _add_empty_categories_to_dict(categories: Dict):
        category_names = [c['category_name'] for c in categories.values()]
        for default_category in [p for p in PROPERTY_CATEGORIES if p not in category_names]:
            category_obj = PropertyCategory.get_cat_by_name(default_category)
            categories[category_obj.id] = {'category_name': category_obj.category_name,
                                           'category_id':   category_obj.id,
                                           'sort':          category_obj.sort,
                                           'properties':    []}

    def get_properties_for_plant(self, plant_id: int) -> List:
        property_objects = PropertyValue.get_by_plant_id(plant_id, raise_exception=False) if plant_id else []
        property_dicts = [p.as_dict() for p in property_objects]

        # build category / property hierarchy
        distinct_categories = set([(p['category_name'], p['category_id'], p['sort'],) for p in property_dicts])
        categories = []
        for c in distinct_categories:
            categories.append(cat := {
                'category_name': c[0],
                'category_id':   c[1],
                'sort':          c[2],
                })
            cat['properties'] = [{
                'property_name':    p['property_name'],
                'property_name_id': p['property_name_id'],
                'property_values':  [
                    {
                        'type':              'plant',
                        'property_value':    p['property_value'],
                        'property_value_id': p['property_value_id']
                        }
                    ]
                } for p in property_dicts if p['category_id'] == cat['category_id']]

        self._add_empty_categories(categories)
        return categories

    def get_properties_for_taxon(self, taxon_id: int) -> Dict[int, Dict]:
        taxon = Taxon.get_taxon_by_taxon_id(taxon_id, raise_exception=True)
        property_objects_taxon = taxon.property_values_taxon
        property_dicts_taxon = [p.as_dict() for p in property_objects_taxon]

        distinct_categories = set([(p['category_name'], p['category_id'], p['sort'],) for p in property_dicts_taxon])
        categories_taxon = {}
        for c in distinct_categories:
            categories_taxon[c[1]] = (cat := {
                'category_name': c[0],
                'category_id':   c[1],
                'sort':          c[2],
                })
            cat['properties'] = [{
                'property_name':    p['property_name'],
                'property_name_id': p['property_name_id'],

                'property_values':  [
                    {
                        'type':              'taxon',
                        'property_value':    p['property_value'],
                        'property_value_id': p['property_value_id']
                        }
                    ]
                } for p in property_dicts_taxon if p['category_id'] == cat['category_id']]
        self._add_empty_categories_to_dict(categories_taxon)
        return categories_taxon


class SaveProperties(MixinShared):

    @staticmethod
    def _is_newly_used_for_plant(property_new: Dict, properties_current: List[PropertyValue]) -> bool:
        property_current = [p for p in properties_current if p.property_name_id == property_new.get(
            'property_name_id')]
        if not property_current:
            return True
        else:
            return False

    @staticmethod
    def _is_modified(property_new: Dict, properties_current: List[PropertyValue]) -> bool:
        # if not property_new.get('property_name_id'):
        #     # new property name
        #     return True
        property_current = [p for p in properties_current if p.property_name_id == property_new[
            'property_name_id']][0]
        if property_current.property_value != property_new['property_value']:
            return True
        else:
            return False

    @staticmethod
    def _new_property_for_plant(plant_id: int, property_modified: Dict):
        property_object = PropertyValue(
                property_name_id=property_modified['property_name_id'],
                property_value=property_modified['property_value'],
                plant_id=plant_id
                )
        return property_object

    @staticmethod
    def _modify_existing_property_value(property_modified):
        property_value_object = PropertyValue.get_by_id(property_modified['property_value_id'],
                                                        raise_exception=True)
        property_value_object.property_value = property_modified['property_value']

    @staticmethod
    def _remove_taxon_properties(categories_modified: List):
        """the frontend sends taxon properties within the plants properties; remove them"""
        for category_modified in [c for c in categories_modified if c.get('properties')]:
            for i, property_name in enumerate(category_modified['properties']):
                if property_name.get('property_values'):
                    property_values_plant = [v for v in property_name['property_values'] if v.get('type') == 'plant']
                    if property_values_plant:
                        # flatten
                        property_name['property_value'] = property_values_plant[0].get('property_value')
                        property_name['property_value_id'] = property_values_plant[0].get('property_value_id')
                        del property_name['property_values']
                    else:
                        # no plant property for this plant_name (only other types like taxon property)
                        # therefore, delete the whole property name node
                        category_modified['properties'].pop(i)

    def _save_categories(self, plant_id, categories_modified: List) -> List:
        # get current properties for the plant
        self._remove_taxon_properties(categories_modified)
        plant = Plant.get_plant_by_plant_id(plant_id, raise_exception=True)
        properties_current = plant.property_values_plant

        new_list = []
        for category_modified in categories_modified:
            if not category_modified.get('properties'):
                continue
            for property_modified in category_modified['properties']:
                if self._is_newly_used_for_plant(property_modified, properties_current):
                    # skip if empty value
                    if not property_modified.get('property_value'):
                        continue
                    # maybe the property name is new, too
                    if not property_modified.get('property_name_id'):
                        property_modified['property_name_id'] = self.create_new_property_name(
                                category_modified['category_id'],
                                property_modified['property_name'])
                    new_list.append(self._new_property_for_plant(plant_id, property_modified))
                elif self._is_modified(property_modified, properties_current):
                    self._modify_existing_property_value(property_modified)

        # identify deleted property values
        ids_current = [p.id for p in properties_current]
        properties_modified = [c['properties'] for c in categories_modified]
        properties_modified_flattened = [p for sublist in properties_modified for p in sublist]
        ids_modified = [p['property_value_id'] for p in properties_modified_flattened if p.get('property_value_id')]
        property_value_ids_deleted = [i for i in ids_current if i not in ids_modified]
        if property_value_ids_deleted:
            self._delete_property_values(property_value_ids_deleted)

        return new_list

    def save_properties(self, properties_modified: Dict):
        for plant_id, plant_values in properties_modified.items():
            new_list = self._save_categories(plant_id, plant_values['categories'])
            if new_list:
                get_sql_session().add_all(new_list)
            get_sql_session().commit()

    @staticmethod
    def _delete_property_values(property_value_ids: List[int]):
        for property_value_id in property_value_ids:
            property_value_object = PropertyValue.get_by_id(property_value_id)
            get_sql_session().delete(property_value_object)


class SavePropertiesTaxa(MixinShared):
    @staticmethod
    def _get_taxon_property_value(property_values: List[dict]):
        property_values = [p for p in property_values if p.get('type') == 'taxon']
        if property_values:
            return property_values[0]

    def _flatten_property(self, property_name_dict):
        """pick the taxon property value among the plant_name property values and set it in property name dict """
        property_value_taxon = self._get_taxon_property_value(property_name_dict['property_values'])
        if property_value_taxon:
            property_name_dict['property_value'] = property_value_taxon['property_value']
            del property_name_dict['property_values']
            return property_name_dict
        else:
            return None

    def save_properties(self, properties_modified: Dict):
        # loop at taxa
        new_list = []
        del_list = []
        for taxon_id, categories_dict in properties_modified.items():
            taxon = Taxon.get_taxon_by_taxon_id(taxon_id, raise_exception=True)

            # nested loop
            for category in categories_dict.values():
                property_values_current = [p for p in taxon.property_values_taxon if p.property_name and
                                           p.property_name.category_id ==
                                           category['category_id']]
                properties = [self._flatten_property(p) for p in category['properties']]

            # property_names_nested = [x['properties'] for x in categories_dict.values()]
            # property_names = [item for sublist in property_names_nested for item in sublist]
            #     properties = [self._flatten_property(p) for p in property_names]
            #     properties = [p for p in properties if p is not None]

                # filter out empty values
                properties = [p for p in properties if p['property_value']]

                # deleted properties
                del_list.extend(self._get_deleted_property_values(properties, property_values_current))
                if del_list:
                    a = 1

                for p in properties:
                    # compare with current property values whether new or deleted
                    if self._is_newly_used_for_taxon(p, property_values_current):
                        # maybe the property name is new, too
                        if not p.get('property_name_id'):
                            p['property_name_id'] = self.create_new_property_name(
                                    category['category_id'],
                                    p['property_name'])
                        new_list.append(self._new_property_value_object(taxon, p))
                    elif self._is_modified(p, property_values_current):
                        self._modify_existing_property_value(p, property_values_current)


        if new_list:
            get_sql_session().add_all(new_list)
        for d in del_list:
            get_sql_session().delete(d)
        get_sql_session().commit()

    @staticmethod
    def _get_deleted_property_values(properties, property_values_current) -> List[PropertyValue]:
        new_property_name_ids = [p.get('property_name_id') for p in properties]
        return[p for p in property_values_current if p.property_name_id not in new_property_name_ids]

    @staticmethod
    def _modify_existing_property_value(property_modified, property_values_current):
        property_value_object = [p for p in property_values_current if p.property_name_id == property_modified[
            'property_name_id']][0]
        property_value_object.property_value = property_modified['property_value']

    @staticmethod
    def _new_property_value_object(taxon: Taxon, property_value_modified: Dict):
        property_value_object = PropertyValue(
                property_name_id=property_value_modified['property_name_id'],
                property_value=property_value_modified.get('property_value'),
                taxon=taxon
                )
        return property_value_object

    @staticmethod
    def _is_newly_used_for_taxon(property_new: Dict, property_values_current: List[PropertyValue]) -> bool:
        if [p for p in property_values_current if p.property_name_id == property_new.get('property_name_id')]:
            return False
        else:
            return True

    @staticmethod
    def _is_modified(property_new: Dict, property_values_current: List[PropertyValue]) -> bool:
        property_current = [p for p in property_values_current if p.property_name_id == property_new[
            'property_name_id']][0]
        if property_current.property_value != property_new['property_value']:
            return True
        else:
            return False

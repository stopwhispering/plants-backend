from typing import List, Dict, Optional

from sqlalchemy import inspect

from plants import constants
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.property.property_dal import PropertyDAL
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.modules.property.models import PropertyValue, PropertyName
from plants.modules.taxon.models import Taxon
from plants.modules.property.schemas import FBPropertiesInCategory, FBProperty, FBPropertyCollectionPlant


class MixinShared:

    def __init__(self, property_dal: PropertyDAL):
        self.property_dal = property_dal

    async def create_new_property_name(self, category_id, property_name):
        """returns newly createad property name's id"""
        category_obj = await self.property_dal.get_property_category_by_id(category_id)
        # make sure it does not already exist
        current_property_names = [p for p in category_obj.property_names if p.property_name == property_name]
        if current_property_names:
            return current_property_names[0].id

        property_name = PropertyName(property_name=property_name, category_id=category_id)
        # we need to add it and flush to get a property name id
        await self.property_dal.create_property_name(property_name)
        return property_name.id


class LoadProperties:

    def __init__(self, property_dal: PropertyDAL, taxon_dal: TaxonDAL):
        self.property_dal = property_dal
        self.taxon_dal = taxon_dal

    async def _add_empty_categories(self, categories: List):
        category_names = [c['category_name'] for c in categories]
        for default_category in [p for p in constants.PROPERTY_CATEGORIES if p not in category_names]:
            category_obj = await self.property_dal.get_property_category_by_name(default_category)
            categories.append({'category_name': category_obj.category_name,
                               'category_id':   category_obj.id,
                               # 'sort':          category_obj.sort,
                               'properties':    []})

    async def _add_empty_categories_to_dict(self, categories: Dict):
        category_names = [c['category_name'] for c in categories.values()]
        for default_category in [p for p in constants.PROPERTY_CATEGORIES if p not in category_names]:
            category_obj = await self.property_dal.get_property_category_by_name(default_category)
            categories[category_obj.id] = {'category_name': category_obj.category_name,
                                           'category_id':   category_obj.id,
                                           # 'sort':          category_obj.sort,
                                           'properties':    []}

    async def get_properties_for_plant(self, plant: Plant) -> List:
        property_objects = await self.property_dal.get_property_values_by_plant_id(plant.id)
        property_dicts = [self._property_value_as_dict(p) for p in property_objects]

        # build category / property hierarchy
        # distinct_categories = set([(p['category_name'], p['category_id'], p['sort'],) for p in property_dicts])
        distinct_categories = set([(p['category_name'], p['category_id'],) for p in property_dicts])
        categories = []
        for c in distinct_categories:
            categories.append(cat := {
                'category_name': c[0],
                'category_id':   c[1],
                # 'sort':          c[2],
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

        await self._add_empty_categories(categories)
        return categories

    @staticmethod
    def _property_value_as_dict(property_value: PropertyValue) -> Dict:
        as_dict = {c.key: getattr(property_value, c.key) for c in inspect(property_value).mapper.column_attrs}
        as_dict['property_value_id'] = property_value.id
        del as_dict['id']
        as_dict['property_name'] = property_value.property_name.property_name
        as_dict['property_name_id'] = property_value.property_name.id
        as_dict['category_name'] = property_value.property_name.property_category.category_name
        as_dict['category_id'] = property_value.property_name.property_category.id
        return as_dict

    async def get_properties_for_taxon(self, taxon_id: int) -> Dict[int, Dict]:
        taxon = await self.taxon_dal.by_id(taxon_id)
        property_objects_taxon = taxon.property_values_taxon
        property_dicts_taxon = [self._property_value_as_dict(p) for p in property_objects_taxon]

        # distinct_categories = set([(p['category_name'], p['category_id'], p['sort'],) for p in property_dicts_taxon])
        distinct_categories = set([(p['category_name'], p['category_id'],) for p in property_dicts_taxon])
        categories_taxon = {}
        for c in distinct_categories:
            categories_taxon[c[1]] = (cat := {
                'category_name': c[0],
                'category_id':   c[1],
                # 'sort':          c[2],
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
        await self._add_empty_categories_to_dict(categories_taxon)
        return categories_taxon


class SaveProperties(MixinShared):

    def __init__(self, property_dal: PropertyDAL, plant_dal: PlantDAL):
        super().__init__(property_dal=property_dal)
        self.property_dal = property_dal
        self.plant_dal = plant_dal

    @staticmethod
    def _is_newly_used_for_plant(property_new: FBProperty, properties_current: List[PropertyValue]) -> bool:
        property_current = [p for p in properties_current if p.property_name_id == property_new.property_name_id]
        if not property_current:
            return True
        else:
            return False

    @staticmethod
    def _is_modified(property_new: FBProperty, properties_current: List[PropertyValue]) -> bool:
        # if not property_new.get('property_name_id'):
        #     # new property name
        #     return True
        property_current = [p for p in properties_current if p.property_name_id == property_new.property_name_id][0]
        if property_current.property_value != property_new.property_value:
            return True
        else:
            return False

    @staticmethod
    def _new_property_for_plant(plant_id: int, property_modified: FBProperty) -> PropertyValue:
        property_object = PropertyValue(
                property_name_id=property_modified.property_name_id,
                property_value=property_modified.property_value,
                plant_id=plant_id
                )
        return property_object

    async def _modify_existing_property_value(self, property_modified: FBProperty):
        # todo is this code outdated? seems to make no sense as there is no prop value id here
        # todo check
        property_value_object = await self.property_dal.get_property_value_by_id(property_modified.property_value_id)
        property_value_object.property_value = property_modified.property_value

    @staticmethod
    def _remove_taxon_properties(categories_modified: List[FBPropertiesInCategory]):
        """the frontend sends taxon properties within the plants properties; remove them"""
        for category_modified in [c for c in categories_modified if c.properties]:
            for i, property_name in enumerate(category_modified.properties):
                if property_name.property_values:
                    property_values_plant = [v for v in property_name.property_values if v.type == 'plant']
                    if property_values_plant:
                        # flatten
                        property_name.property_value = property_values_plant[0].property_value
                        property_name.property_value_id = property_values_plant[0].property_value_id
                        del property_name.property_values
                    else:
                        # no plant property for this plant_name (only other types like taxon property)
                        # therefore, delete the whole property name node
                        category_modified.properties.pop(i)

    async def _save_categories(self, plant_id, categories_modified: List[FBPropertiesInCategory]) -> list[PropertyValue]:
        # get current properties for the plant
        self._remove_taxon_properties(categories_modified)
        plant = await self.plant_dal.by_id(plant_id)
        properties_current = plant.property_values_plant

        new_list: list[PropertyValue] = []
        for category_modified in categories_modified:
            if not category_modified.properties:
                continue
            for property_modified in category_modified.properties:
                if self._is_newly_used_for_plant(property_modified, properties_current):
                    # skip if empty value
                    if not property_modified.property_value:
                        continue
                    # maybe the property name is new, too
                    if not property_modified.property_name_id:
                        property_modified.property_name_id = await self.create_new_property_name(
                                category_modified.category_id,
                                property_modified.property_name)
                    new_list.append(self._new_property_for_plant(plant_id, property_modified))
                elif self._is_modified(property_modified, properties_current):
                    await self._modify_existing_property_value(property_modified)

        # identify deleted property values
        ids_current = [p.id for p in properties_current]
        properties_modified = [c.properties for c in categories_modified]
        properties_modified_flattened = [p for sublist in properties_modified for p in sublist]
        # todo check
        ids_modified = [p.property_value_id for p in properties_modified_flattened if p.property_value_id]
        property_value_ids_deleted = [i for i in ids_current if i not in ids_modified]
        if property_value_ids_deleted:
            await self._delete_property_values(property_value_ids_deleted)

        return new_list

    async def save_properties(self, properties_modified: Dict[int, FBPropertyCollectionPlant]):
        for plant_id, plant_values in properties_modified.items():
            new_list: list[PropertyValue] = await self._save_categories(plant_id, plant_values.categories)
            if new_list:
                await self.property_dal.create_property_values(new_list)

    async def _delete_property_values(self, property_value_ids: List[int]):
        for property_value_id in property_value_ids:
            property_value_object = await self.property_dal.get_property_value_by_id(property_value_id)
            await self.property_dal.delete_property_value(property_value_object)


class SavePropertiesTaxa(MixinShared):

    def __init__(self, property_dal: PropertyDAL, taxon_dal: TaxonDAL):
        super().__init__(property_dal=property_dal)
        self.property_dal = property_dal
        self.taxon_dal = taxon_dal

    @staticmethod
    def _get_taxon_property_value(property_values: list[PropertyValue]) -> PropertyValue | None:
        property_values = [p for p in property_values if p.type == 'taxon']
        if property_values:
            return property_values[0]

    def _flatten_property(self, property_name_dict: FBProperty) -> Optional[FBProperty]:
        """pick the taxon property value among the plant_name property values and set it in property name dict """
        # todo this seems messeup -> cleanup or remove functionality
        property_value_taxon = self._get_taxon_property_value(property_name_dict.property_values)
        if property_value_taxon:
            property_name_dict.property_value = property_value_taxon.property_value
            del property_name_dict.property_values
            return property_name_dict
        else:
            return None

    async def save_properties(self, properties_modified: Dict[int, Dict[int, FBPropertiesInCategory]]):
        # loop at taxa
        new_list: list[PropertyValue] = []
        del_list: list[PropertyValue] = []
        for taxon_id, categories_dict in properties_modified.items():
            taxon = await self.taxon_dal.by_id(taxon_id)

            # nested loop
            for category in categories_dict.values():
                property_values_current = [p for p in taxon.property_values_taxon if p.property_name and
                                           p.property_name.category_id ==
                                           category.category_id]
                properties = [self._flatten_property(p) for p in category.properties]

                # filter out empty values
                properties = [p for p in properties if p and p.property_value]

                # deleted properties
                del_list.extend(self._get_deleted_property_values(properties, property_values_current))

                for p in properties:
                    # compare with current property values whether new or deleted
                    if self._is_newly_used_for_taxon(p, property_values_current):
                        # maybe the property name is new, too
                        if not p.property_name_id:
                            p.property_name_id = await self.create_new_property_name(
                                    category.category_id,
                                    p.property_name)
                        new_list.append(self._new_property_value_object(taxon, p))
                    elif self._is_modified(p, property_values_current):
                        self._modify_existing_property_value(p, property_values_current)

        if new_list:
            await self.property_dal.create_property_values(new_list)
        if del_list:
            await self.property_dal.delete_property_values(del_list)

    @staticmethod
    def _get_deleted_property_values(properties, property_values_current) -> List[PropertyValue]:
        new_property_name_ids = [p.property_name_id for p in properties]
        return[p for p in property_values_current if p.property_name_id not in new_property_name_ids]

    @staticmethod
    def _modify_existing_property_value(property_modified: FBProperty, property_values_current):
        property_value_object = [p for p in property_values_current if p.property_name_id ==
                                 property_modified.property_name_id][0]
        property_value_object.property_value = property_modified.property_value

    @staticmethod
    def _new_property_value_object(taxon: Taxon, property_value_modified: FBProperty) -> PropertyValue:
        property_value_object = PropertyValue(
                property_name_id=property_value_modified.property_name_id,
                property_value=property_value_modified.property_value,
                taxon=taxon
                )
        return property_value_object

    @staticmethod
    def _is_newly_used_for_taxon(property_new: FBProperty, property_values_current: List[PropertyValue]) -> bool:
        if [p for p in property_values_current if p.property_name_id == property_new.property_name_id]:
            return False
        else:
            return True

    @staticmethod
    def _is_modified(property_new: FBProperty, property_values_current: List[PropertyValue]) -> bool:
        property_current = [p for p in property_values_current if p.property_name_id ==
                            property_new.property_name_id][0]
        if property_current.property_value != property_new.property_value:
            return True
        else:
            return False

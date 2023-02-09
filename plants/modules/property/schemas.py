from typing import Dict, List, Optional

from pydantic import constr

from plants.shared.base_schema import BaseSchema, RequestContainer, ResponseContainer


class FBPropertyValue(BaseSchema):
    type: str
    property_value: constr(min_length=1, max_length=240)
    property_value_id: Optional[int]  # missing if new


# todo make all this flatter and easier
class FBProperty(BaseSchema):
    property_name: constr(min_length=1, max_length=240)
    property_name_id: Optional[int]  # empty if new
    property_values: List[FBPropertyValue]
    property_value: Optional[constr(min_length=1, max_length=240)]  # after flattening
    property_value_id: Optional[int]  # set at certain point from property values list


class FBPropertiesInCategory(BaseSchema):
    category_name: constr(min_length=1, max_length=80)
    category_id: int
    properties: List[FBProperty]
    # used in some request to add new property to category
    property_value: Optional[constr(min_length=1, max_length=240)]


# todo unite taxon & plant
class FBPropertyCollectionPlant(BaseSchema):  # todo useless with only one key
    categories: List[FBPropertiesInCategory]


class FPropertiesModifiedPlant(RequestContainer):
    modifiedPropertiesPlants: Dict[int, FBPropertyCollectionPlant]


class FPropertiesModifiedTaxon(RequestContainer):
    modifiedPropertiesTaxa: Dict[int, Dict[int, FBPropertiesInCategory]]


class BPropertyName(BaseSchema):
    property_name_id: Optional[int]  # None if new
    property_name: str
    countPlants: int


class BResultsPropertyNames(ResponseContainer):
    propertiesAvailablePerCategory: Dict[str, List[BPropertyName]]


class BPropertyCollectionTaxon(BaseSchema):  # todo useless with only one key
    categories: Dict[int, FBPropertiesInCategory]  # todo why a dict here?


class BResultsPropertiesForPlant(ResponseContainer):
    propertyCollections: FBPropertyCollectionPlant
    plant_id: int
    propertyCollectionsTaxon: BPropertyCollectionTaxon
    taxon_id: Optional[int]

from typing import Dict, List, Optional

from pydantic import Extra
from pydantic.main import BaseModel

from plants.validation.message_validation import PMessage


class PPropertyName(BaseModel):
    property_name_id: Optional[int]  # None if new
    property_name: str
    countPlants: int

    class Config:
        extra = Extra.forbid


class PResultsPropertyNames(BaseModel):
    action: str
    resource: str
    message: PMessage
    propertiesAvailablePerCategory: Dict[str, List[PPropertyName]]

    class Config:
        extra = Extra.forbid


class PPropertyValue(BaseModel):
    type: str
    property_value: str
    property_value_id: Optional[int]  # missing if new

    class Config:
        extra = Extra.forbid


# todo make all this flatter and easier
class PProperty(BaseModel):
    property_name: str
    property_name_id: Optional[int]  # empty if new
    property_values: List[PPropertyValue]
    property_value: Optional[str]  # after flattening
    property_value_id: Optional[int]  # set at certain point from property values list

    class Config:
        extra = Extra.forbid


class PPropertiesInCategory(BaseModel):
    category_name: str
    category_id: int
    sort: Optional[int]  # todo remove?
    properties: List[PProperty]
    property_value: Optional[str]  # used in some request to add new property to category

    class Config:
        extra = Extra.forbid


# todo unite taxon & plant
class PPropertyCollectionPlant(BaseModel):  # todo useless with only one key
    categories: List[PPropertiesInCategory]

    class Config:
        extra = Extra.forbid


class PPropertyCollectionTaxon(BaseModel):  # todo useless with only one key
    categories: Dict[int, PPropertiesInCategory]  # todo why a dict here?

    class Config:
        extra = Extra.forbid


class PResultsPropertiesForPlant(BaseModel):
    action: str
    resource: str
    message: PMessage
    propertyCollections: PPropertyCollectionPlant
    plant_id: int
    propertyCollectionsTaxon: PPropertyCollectionTaxon
    taxon_id: Optional[int]

    class Config:
        extra = Extra.forbid


class PPropertiesModifiedPlant(BaseModel):
    modifiedPropertiesPlants: Dict[int, PPropertyCollectionPlant]

    class Config:
        extra = Extra.forbid


class PPropertiesModifiedTaxon(BaseModel):
    modifiedPropertiesTaxa: Dict[int, Dict[int, PPropertiesInCategory]]

    class Config:
        extra = Extra.forbid

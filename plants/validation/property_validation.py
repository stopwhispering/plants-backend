from typing import Dict, List, Optional

from pydantic import Extra
from pydantic.main import BaseModel

from plants.validation.message_validation import BMessage


####################################################################################################
# Entities used in both API Requests from Frontend and Responses from Backend (FB...)
####################################################################################################
class FBPropertyValue(BaseModel):
    type: str
    property_value: str
    property_value_id: Optional[int]  # missing if new

    class Config:
        extra = Extra.forbid


# todo make all this flatter and easier
class FBProperty(BaseModel):
    property_name: str
    property_name_id: Optional[int]  # empty if new
    property_values: List[FBPropertyValue]
    property_value: Optional[str]  # after flattening
    property_value_id: Optional[int]  # set at certain point from property values list

    class Config:
        extra = Extra.forbid


class FBPropertiesInCategory(BaseModel):
    category_name: str
    category_id: int
    sort: Optional[int]  # todo remove?
    properties: List[FBProperty]
    property_value: Optional[str]  # used in some request to add new property to category

    class Config:
        extra = Extra.forbid


# todo unite taxon & plant
class FBPropertyCollectionPlant(BaseModel):  # todo useless with only one key
    categories: List[FBPropertiesInCategory]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API Requests from Frontend (F...)
####################################################################################################
class FPropertiesModifiedPlant(BaseModel):
    modifiedPropertiesPlants: Dict[int, FBPropertyCollectionPlant]

    class Config:
        extra = Extra.forbid


class FPropertiesModifiedTaxon(BaseModel):
    modifiedPropertiesTaxa: Dict[int, Dict[int, FBPropertiesInCategory]]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API Responses from Backend (B...)
####################################################################################################
class BPropertyName(BaseModel):
    property_name_id: Optional[int]  # None if new
    property_name: str
    countPlants: int

    class Config:
        extra = Extra.forbid


class BResultsPropertyNames(BaseModel):
    action: str
    resource: str
    message: BMessage
    propertiesAvailablePerCategory: Dict[str, List[BPropertyName]]

    class Config:
        extra = Extra.forbid


class BPropertyCollectionTaxon(BaseModel):  # todo useless with only one key
    categories: Dict[int, FBPropertiesInCategory]  # todo why a dict here?

    class Config:
        extra = Extra.forbid


class BResultsPropertiesForPlant(BaseModel):
    action: str
    resource: str
    message: BMessage
    propertyCollections: FBPropertyCollectionPlant
    plant_id: int
    propertyCollectionsTaxon: BPropertyCollectionTaxon
    taxon_id: Optional[int]

    class Config:
        extra = Extra.forbid

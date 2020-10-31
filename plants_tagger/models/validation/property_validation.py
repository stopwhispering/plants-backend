from typing import Dict, List, Optional
from pydantic.main import BaseModel

from plants_tagger.models.validation.message_validation import PMessage
from plants_tagger.models.validation.plant_validation import PPlantId
from plants_tagger.models.validation.taxon_validation import PTaxonId


class PCategoryId(BaseModel):
    __root__: int


class PPropertyName(BaseModel):
    property_name_id: int
    property_name: str
    countPlants: int

    class Config:
        extra = 'forbid'


class PResultsPropertyNames(BaseModel):
    action: str
    resource: str
    message: PMessage
    propertiesAvailablePerCategory: Dict[str, List[PPropertyName]]

    class Config:
        extra = 'forbid'


class PropertyValue(BaseModel):
    type: str
    property_value: str
    property_value_id: Optional[int]  # missing if new

    class Config:
        extra = 'forbid'


# todo make all this flatter and easier
class Property(BaseModel):
    property_name: str
    property_name_id: int
    property_values: List[PropertyValue]

    class Config:
        extra = 'forbid'


class PropertiesInCategory(BaseModel):
    category_name: str
    category_id: PCategoryId
    sort: Optional[int]  # todo remove?
    properties: List[Property]

    class Config:
        extra = 'forbid'


# todo unite taxon & plant
class PPropertyCollectionPlant(BaseModel):  # todo useless with only one key
    categories: List[PropertiesInCategory]

    class Config:
        extra = 'forbid'


class PPropertyCollectionTaxon(BaseModel):  # todo useless with only one key
    categories: Dict[int, PropertiesInCategory]  # todo why a dict here?

    class Config:
        extra = 'forbid'


class PResultsPropertiesForPlant(BaseModel):
    action: str
    resource: str
    message: PMessage
    propertyCollections: PPropertyCollectionPlant
    plant_id: PPlantId
    propertyCollectionsTaxon: PPropertyCollectionTaxon
    taxon_id: PTaxonId

    class Config:
        extra = 'forbid'


class PPropertiesModifiedPlant(BaseModel):
    modifiedPropertiesPlants: Dict[int, PPropertyCollectionPlant]


class PPropertiesModifiedTaxon(BaseModel):
    modifiedPropertiesTaxa: Dict[int, Dict[int, PropertiesInCategory]]

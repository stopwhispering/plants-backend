from enum import Enum
from typing import Optional

from pydantic import Extra
from pydantic.main import BaseModel


####################################################################################################
# Entities used in <<both>> API Requests from Frontend <<and>> Responses from Backend (FB...)
####################################################################################################


####################################################################################################
# Entities used only in API <<Requests>> from <<Frontend>> (F...)
####################################################################################################


####################################################################################################
# Entities used only in API <<Responses>> from <<Backend>> B...)
####################################################################################################
class BMessageType(Enum):
    """message types processed by error/success handlers in ui5 web frontend"""
    INFORMATION = 'Information'
    NONE = 'None'
    SUCCESS = 'Success'
    WARNING = 'Warning'
    ERROR = 'Error'
    DEBUG = 'Debug'  # not known by UI5 message processor, only shown in frontend console log


class BMessage(BaseModel):
    type: BMessageType
    message: str
    additionalText: Optional[str]
    description: Optional[str]

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class BConfirmation(BaseModel):
    action: str
    message: BMessage

    class Config:
        extra = Extra.forbid


class FBMajorResource(Enum):
    PLANT = "PlantResource"
    IMAGE = "ImageResource"
    TAXON = "TaxonResource"
    EVENT = "EventResource"
    PLANT_PROPERTIES = "PlantPropertyResource"
    TAXON_PROPERTIES = "TaxonPropertyResource"


class BSaveConfirmation(BaseModel):
    """
    for the major resources (plants, images, taxa, events, palnt properties, taxon properties,
    we need to return the updated resource to the frontend
    to enable the frontend to identify when all resources have been saved
    """
    resource: FBMajorResource
    message: BMessage

    class Config:
        use_enum_values = True
        extra = Extra.forbid

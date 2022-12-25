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
    DEBUG = 'Debug'  # not known by UI5 message processor, only showed in frontend console log


class BMessage(BaseModel):
    type: BMessageType
    message: str
    additionalText: Optional[str]
    description: Optional[str]

    class Config:
        extra = Extra.forbid


class BConfirmation(BaseModel):
    action: str
    resource: str
    message: BMessage

    class Config:
        extra = Extra.forbid

from enum import Enum

from pydantic import Extra
from pydantic.main import BaseModel
from typing import List, Optional

from plants.validation.message_validation import BMessage


####################################################################################################
# Entities used in both API Requests from Frontend and Responses from Backend (FB...)
####################################################################################################


####################################################################################################
# Entities used only in API <<Requests>> from <<Frontend>> (F...)
####################################################################################################
class FProposalEntity(str, Enum):
    """proposal entities that may be requested by frontend"""
    SOIL = 'SoilProposals'
    NURSERY = 'NurserySourceProposals'
    KEYWORD = 'KeywordProposals'


####################################################################################################
# Entities used only in API <<Responses>> from <<Backend>> (B...)
####################################################################################################
class BKeywordName(BaseModel):
    keyword: str

    class Config:
        extra = Extra.forbid


class BNurseryName(BaseModel):
    name: str

    class Config:
        extra = Extra.forbid


class BResultsProposals(BaseModel):
    action: str
    resource: str
    message: BMessage

    NurseriesSourcesCollection: Optional[List[BNurseryName]]
    KeywordsCollection: Optional[List[BKeywordName]]
    # TraitCategoriesCollection: Optional[List[PTraitCategory]]
    # TraitsCollection: Optional[List[PTrait]]

    class Config:
        extra = Extra.forbid

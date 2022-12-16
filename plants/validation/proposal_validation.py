from enum import Enum

from pydantic import Extra
from pydantic.main import BaseModel
from typing import List, Optional

from plants.validation.message_validation import PMessage
from plants.validation.trait_validation import PTraitCategory, PTrait


class ProposalEntity(str, Enum):
    """proposal entities that may be requested by frontend"""
    SOIL = 'SoilProposals'
    NURSERY = 'NurserySourceProposals'
    KEYWORD = 'KeywordProposals'
    TRAIT_CATEGORY = 'TraitCategoryProposals'


class PComponentName(BaseModel):
    component_name: str

    class Config:
        extra = Extra.forbid


class PNurseryName(BaseModel):
    name: str

    class Config:
        extra = Extra.forbid


class PKeywordName(BaseModel):
    keyword: str

    class Config:
        extra = Extra.forbid


class PResultsProposals(BaseModel):
    action: str
    resource: str
    message: PMessage

    NurseriesSourcesCollection: Optional[List[PNurseryName]]
    KeywordsCollection: Optional[List[PKeywordName]]
    TraitCategoriesCollection: Optional[List[PTraitCategory]]
    TraitsCollection: Optional[List[PTrait]]

    class Config:
        extra = Extra.forbid

from enum import Enum

from pydantic.main import BaseModel
from typing import List, Optional

from plants_tagger.validation.event_validation import PSoil
from plants_tagger.validation.message_validation import PMessage
from plants_tagger.validation.trait_validation import PTraitCategory, PTrait


class ProposalEntity(str, Enum):
    """proposal entities that may be requested by frontend"""
    SOIL = 'SoilProposals'
    NURSERY = 'NurserySourceProposals'
    KEYWORD = 'KeywordProposals'
    TRAIT_CATEGORY = 'TraitCategoryProposals'


class PEntityName(BaseModel):
    __root__: ProposalEntity

    class Config:
        extra = 'forbid'


class PComponentName(BaseModel):
    component_name: str

    class Config:
        extra = 'forbid'


class PNurseryName(BaseModel):
    name: str

    class Config:
        extra = 'forbid'


class PKeywordName(BaseModel):
    keyword: str

    class Config:
        extra = 'forbid'


class PResultsProposals(BaseModel):
    action: str
    resource: str
    message: PMessage

    SoilsCollection: Optional[List[PSoil]]
    ComponentsCollection: Optional[List[PComponentName]]

    NurseriesSourcesCollection: Optional[List[PNurseryName]]

    KeywordsCollection: Optional[List[PKeywordName]]

    TraitCategoriesCollection: Optional[List[PTraitCategory]]
    TraitsCollection: Optional[List[PTrait]]

    class Config:
        extra = 'forbid'

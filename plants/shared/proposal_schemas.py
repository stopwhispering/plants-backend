from __future__ import annotations

from enum import Enum

from pydantic import Extra
from pydantic.main import BaseModel
from typing import List, Optional

from plants.shared.message_schemas import BMessage


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
class BKeywordProposal(BaseModel):
    keyword: str

    class Config:
        extra = Extra.forbid


class BNurseryProposal(BaseModel):
    name: str

    class Config:
        extra = Extra.forbid


class BResultsProposals(BaseModel):
    action: str
    message: BMessage

    NurseriesSourcesCollection: Optional[List[BNurseryProposal]]
    KeywordsCollection: Optional[List[BKeywordProposal]]  # todo remove

    class Config:
        extra = Extra.forbid


class BTaxonTreeNode(BaseModel):
    key: str
    level: int
    count: int
    nodes: Optional[List[BTaxonTreeNode]]  # missing on lowest level
    plant_ids: Optional[List[int]]  # plants themselves on lowest level

    class Config:
        extra = Extra.forbid


# this is required (plus importing annotations) to allow for self-references
BTaxonTreeNode.update_forward_refs()


class BTaxonTreeRoot(BaseModel):
    TaxonTree: List[BTaxonTreeNode]

    class Config:
        extra = Extra.forbid


class BResultsSelection(BaseModel):
    action: str
    message: BMessage
    Selection: BTaxonTreeRoot

    class Config:
        extra = Extra.forbid

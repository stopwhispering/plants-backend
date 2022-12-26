from __future__ import annotations
from typing import Optional, List

from pydantic import Extra
from pydantic.main import BaseModel

from plants.validation.message_validation import BMessage

####################################################################################################
# Entities used in <<both>> API Requests from Frontend <<and>> Responses from Backend (FB...)
####################################################################################################


####################################################################################################
# Entities used only in API <<Requests>> from <<Frontend>> (F...)
####################################################################################################


####################################################################################################
# Entities used only in API <<Responses>> from <<Backend>> B...)
####################################################################################################
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

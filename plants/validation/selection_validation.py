from __future__ import annotations
from typing import Optional, List

from pydantic.main import BaseModel

from plants.validation.message_validation import PMessage


class PTaxonTreeNode(BaseModel):
    key: str
    level: int
    count: int
    nodes: Optional[List[PTaxonTreeNode]]  # not on lowest level
    plant_ids: Optional[List[int]]  # plants themselves on lowest level

    class Config:
        extra = 'forbid'


# this is required (plus importing annotations) to allow for self-references
PTaxonTreeNode.update_forward_refs()


class PTaxonTreeRoot(BaseModel):
    TaxonTree: List[PTaxonTreeNode]

    class Config:
        extra = 'forbid'


class PResultsSelection(BaseModel):
    action: str
    resource: str
    message: PMessage
    Selection: PTaxonTreeRoot

    class Config:
        extra = 'forbid'

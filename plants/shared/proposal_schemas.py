from __future__ import annotations

from typing import Optional

from plants.shared.base_schema import BaseSchema, ResponseContainer
from plants.shared.message_schemas import BMessage


class BKeywordProposal(BaseSchema):
    keyword: str


class BNurseryProposal(BaseSchema):
    name: str


class BResultsProposals(ResponseContainer):
    NurseriesSourcesCollection: Optional[list[BNurseryProposal]]
    KeywordsCollection: Optional[list[BKeywordProposal]]


class BTaxonTreeNode(BaseSchema):
    key: str
    level: int
    count: int
    nodes: Optional[list[BTaxonTreeNode]]  # missing on lowest level
    plant_ids: Optional[list[int]]  # plants themselves on lowest level


# this is required (plus importing annotations) to allow for self-references
BTaxonTreeNode.update_forward_refs()


class BTaxonTreeRoot(BaseSchema):
    TaxonTree: list[BTaxonTreeNode]


class BResultsSelection(ResponseContainer):
    action: str
    message: BMessage
    Selection: BTaxonTreeRoot

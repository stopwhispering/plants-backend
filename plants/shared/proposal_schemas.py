from __future__ import annotations

from typing import List, Optional

from plants.shared.base_schema import BaseSchema, ResponseContainer
from plants.shared.message_schemas import BMessage


class BKeywordProposal(BaseSchema):
    keyword: str


class BNurseryProposal(BaseSchema):
    name: str


class BResultsProposals(ResponseContainer):
    NurseriesSourcesCollection: Optional[List[BNurseryProposal]]
    KeywordsCollection: Optional[List[BKeywordProposal]]  # todo remove


class BTaxonTreeNode(BaseSchema):
    key: str
    level: int
    count: int
    nodes: Optional[List[BTaxonTreeNode]]  # missing on lowest level
    plant_ids: Optional[List[int]]  # plants themselves on lowest level


# this is required (plus importing annotations) to allow for self-references
BTaxonTreeNode.update_forward_refs()


class BTaxonTreeRoot(BaseSchema):
    TaxonTree: List[BTaxonTreeNode]


class BResultsSelection(ResponseContainer):
    action: str
    message: BMessage
    Selection: BTaxonTreeRoot

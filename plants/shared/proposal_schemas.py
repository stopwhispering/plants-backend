from __future__ import annotations

from plants.shared.base_schema import BaseSchema, ResponseContainer
from plants.shared.message_schemas import BMessage


class BKeywordProposal(BaseSchema):
    keyword: str


class BNurseryProposal(BaseSchema):
    name: str


class BResultsProposals(ResponseContainer):
    NurseriesSourcesCollection: list[BNurseryProposal] | None
    KeywordsCollection: list[BKeywordProposal] | None


class BTaxonTreeNode(BaseSchema):
    key: str
    level: int
    count: int
    nodes: list[BTaxonTreeNode] = []  # missing on lowest level
    plant_ids: list[int] = []  # plants themselves on lowest level


# this is required (plus importing annotations) to allow for self-references
BTaxonTreeNode.update_forward_refs()


class BTaxonTreeRoot(BaseSchema):
    TaxonTree: list[BTaxonTreeNode]


class BResultsSelection(ResponseContainer):
    action: str
    message: BMessage
    Selection: BTaxonTreeRoot

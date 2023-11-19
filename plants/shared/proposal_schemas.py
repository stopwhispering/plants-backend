from __future__ import annotations

from plants.shared.base_schema import BaseSchema, ResponseContainer
from plants.shared.message_schemas import BMessage


class BKeywordProposal(BaseSchema):
    keyword: str


class BNurseryProposal(BaseSchema):
    name: str


class BResultsProposals(ResponseContainer):
    NurseriesSourcesCollection: list[BNurseryProposal] | None = None
    KeywordsCollection: list[BKeywordProposal] | None = None


class BTaxonTreeNode(BaseSchema):
    key: str
    level: int
    count: int
    # note: linter wants us to annotate mutable class attributes with `typing.ClassVar`
    # this, however, is not supported by pydantic and results in a total mess
    nodes: list[BTaxonTreeNode] = []  # noqa: RUF012 # missing on lowest level
    # nodes: ClassVar[list[BTaxonTreeNode]] = []  # missing on lowest level
    plant_ids: list[int] = []  # noqa: RUF012 # plants themselves on lowest level
    # plant_ids: ClassVar[list[int]] = []  # plants themselves on lowest level


# this is required (plus importing annotations) to allow for self-references
BTaxonTreeNode.update_forward_refs()


class BTaxonTreeRoot(BaseSchema):
    TaxonTree: list[BTaxonTreeNode]


class BResultsSelection(ResponseContainer):
    action: str
    message: BMessage
    Selection: BTaxonTreeRoot

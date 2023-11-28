from __future__ import annotations

from plants.shared.base_schema import BaseSchema, ResponseContainer


class KeywordProposal(BaseSchema):
    keyword: str


class NurseryProposal(BaseSchema):
    name: str


class GetProposalsResponse(ResponseContainer):
    NurseriesSourcesCollection: list[NurseryProposal] | None = None
    KeywordsCollection: list[KeywordProposal] | None = None


class TaxonTreeNode(BaseSchema):
    key: str
    level: int
    count: int
    # note: linter wants us to annotate mutable class attributes with `typing.ClassVar`
    # this, however, is not supported by pydantic and results in a total mess
    nodes: list[TaxonTreeNode] = []  # noqa: RUF012 # missing on lowest level
    # nodes: ClassVar[list[BTaxonTreeNode]] = []  # missing on lowest level
    plant_ids: list[int] = []  # noqa: RUF012 # plants themselves on lowest level
    # plant_ids: ClassVar[list[int]] = []  # plants themselves on lowest level


# this is required (plus importing annotations) to allow for self-references
# TaxonTreeNode.update_forward_refs()
TaxonTreeNode.model_rebuild()


class TaxonTreeRoot(BaseSchema):
    TaxonTree: list[TaxonTreeNode]


class GetSelectionDataResponse(ResponseContainer):
    Selection: TaxonTreeRoot

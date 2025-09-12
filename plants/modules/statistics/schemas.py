from __future__ import annotations

from plants.shared.base_schema import (
    BaseSchema,
    ResponseContainer,
)


class PollinationStatisticsRow(BaseSchema):
    period: str
    label: str
    value: str


class PollinationStatisticsRead(BaseSchema):
    texts_tabular: list[PollinationStatisticsRow]


class GetPollinationStatisticsResponse(ResponseContainer):
    statistics: PollinationStatisticsRead

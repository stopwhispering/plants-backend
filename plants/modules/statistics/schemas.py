from __future__ import annotations

from plants.shared.base_schema import (
    BaseSchema,
    ResponseContainer,
)


class StatisticsRow(BaseSchema):
    period: str
    label: str
    value: str


class StatisticsRead(BaseSchema):
    texts_tabular: list[StatisticsRow]


class GetStatisticsResponse(ResponseContainer):
    statistics: StatisticsRead

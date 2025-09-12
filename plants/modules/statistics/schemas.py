from __future__ import annotations

from plants.shared.base_schema import (
    BaseSchema,
    ResponseContainer,
)


class PollinationStatisticsRead(BaseSchema):
    n_recent_pollinations_still_open: int
    n_recent_pollinations_successful: int
    n_recent_pollinations_failed: int


class GetPollinationStatisticsResponse(ResponseContainer):
    statistics: PollinationStatisticsRead

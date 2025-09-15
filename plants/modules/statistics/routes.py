from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from plants.dependencies import get_pollination_dal, get_statistics_dal
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.statistics.schemas import GetPollinationStatisticsResponse
from plants.modules.statistics.services import assemble_pollination_statistics
from plants.modules.statistics.statistics_dal import StatisticsDAL
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
    responses={404: {"description": "Not found"}},
)


@router.get("/pollination_statistics", response_model=GetPollinationStatisticsResponse)
async def get_pollination_statistics(
    statistics_dal: StatisticsDAL = Depends(get_statistics_dal),
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
) -> Any:
    """Read settings from settings table."""
    statistics = await assemble_pollination_statistics(statistics_dal, pollination_dal)
    return {
        "action": "Get pollination statistics",
        "message": get_message("Loaded pollination statistics from database."),
        "statistics": statistics,
    }

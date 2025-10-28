from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from plants.dependencies import get_pollination_dal, get_statistics_dal, get_seed_planting_dal
from plants.modules.pollination.pollination_dal import PollinationDAL
from plants.modules.pollination.seed_planting_dal import SeedPlantingDAL
from plants.modules.statistics.schemas import GetStatisticsResponse, StatisticsRead
from plants.modules.statistics.services import assemble_pollination_statistics, \
    assemble_seed_planting_statistics
from plants.modules.statistics.statistics_dal import StatisticsDAL
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
    responses={404: {"description": "Not found"}},
)


@router.get("/pollination_statistics", response_model=GetStatisticsResponse)
async def get_pollination_statistics(
    statistics_dal: StatisticsDAL = Depends(get_statistics_dal),
    pollination_dal: PollinationDAL = Depends(get_pollination_dal),
    seed_planting_dal: SeedPlantingDAL = Depends(get_seed_planting_dal),
) -> Any:
    """Read settings from settings table."""
    pollination_statistics = await assemble_pollination_statistics(statistics_dal, pollination_dal)
    seed_planting_statistics = await assemble_seed_planting_statistics(statistics_dal, seed_planting_dal)
    statistics = pollination_statistics + seed_planting_statistics
    # order by st.period, descending, but '2020-10' before '2020-9' etc.
    statistics = sorted(
        statistics,
        key=lambda st: (st.period.split("-")[0], int(st.period.split("-")[1]) if "-" in st.period else 0),
        reverse=True,
    )

    statistics = StatisticsRead(texts_tabular=statistics)
    return {
        "action": "Get pollination and seed planting statistics",
        "message": get_message("Loaded pollination and seed planting statistics from database."),
        "statistics": statistics,
    }

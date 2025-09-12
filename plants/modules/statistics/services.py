from __future__ import annotations

from typing import TYPE_CHECKING

from plants.modules.pollination.enums import PollinationStatus
from plants.modules.statistics.schemas import PollinationStatisticsRead

if TYPE_CHECKING:
    from plants.modules.pollination.pollination_dal import PollinationDAL
    from plants.modules.statistics.statistics_dal import StatisticsDAL


async def assemble_pollination_settings(
    statistics_dal: StatisticsDAL,  # noqa
    pollination_dal: PollinationDAL,
) -> PollinationStatisticsRead:
    """Read pollinations from pollination table and generate statistics." some explanations:

    * cancelling (submit and set finished) an attempt (green) keeps status unchanged but sets ongoing to False
    * cancelling (submit and set finished) a pollinated one (brown) keeps status unchanged but sets ongoing to False
    * setting a pollinated one (brown) to seed status (no plantings, yet) (removes it from upper list
      and inserts it into lower list) keeps it ongoing but changes status to PollinationStatus.SEED
    * setting the seed planting to germinated and creating a plant does not change status or ongoing
    * finally submitting the pollination sets ongoing to false but keeps status unchanged (it may still
      be considered recent if the florescence is still flowering or has other ongoing pollinations)
    """
    # recent pollinations include (a) all ongoing pollinations, and
    # (b) all finished pollinations of a florescence that is still flowering or has ongoing pollinations
    recent_pollinations = await pollination_dal.get_pollinations(
        include_ongoing_pollinations=True,
        include_recently_finished_pollinations=True,
        include_finished_pollinations=False,
    )

    n_recent_pollinations_still_open = len(
        [
            p
            for p in recent_pollinations
            if p.ongoing and p.pollination_status == PollinationStatus.ATTEMPT
        ]
    )
    n_recent_pollinations_successful = len(
        [
            p
            for p in recent_pollinations
            if p.ongoing and p.pollination_status != PollinationStatus.ATTEMPT
        ]
    )
    # we're ignoring successful pollinations that were aborted for whatever reason (e.g. damage)
    n_recent_pollinations_failed = len(
        [
            p
            for p in recent_pollinations
            if not p.ongoing and p.pollination_status == PollinationStatus.ATTEMPT
        ]
    )

    return PollinationStatisticsRead(
        n_recent_pollinations_still_open=n_recent_pollinations_still_open,
        n_recent_pollinations_successful=n_recent_pollinations_successful,
        n_recent_pollinations_failed=n_recent_pollinations_failed,
    )

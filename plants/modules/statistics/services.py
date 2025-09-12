from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from plants.modules.pollination.enums import FlorescenceStatus, PollinationStatus
from plants.modules.statistics.schemas import PollinationStatisticsRead, PollinationStatisticsRow

if TYPE_CHECKING:
    from plants.modules.pollination.models import Pollination
    from plants.modules.pollination.pollination_dal import PollinationDAL
    from plants.modules.statistics.statistics_dal import StatisticsDAL


def compute_pollination_statistics_for_month(
    pollinations: list[Pollination],
    *,
    recent: bool = False,
    year: int | None = None,
    month: int | None = None,
) -> list[PollinationStatisticsRow]:
    """# recent pollinations include (a) all ongoing pollinations, and

    # (b) all finished pollinations of a florescence that is still flowering or has ongoing
    pollinations; cf. pollination_dal.get_pollinations()
    """

    if recent:
        assert year is None and month is None  # noqa
        period = "Recent"
        pollinations = [
            p
            for p in pollinations
            if p.ongoing
            or (p.florescence and p.florescence.florescence_status == FlorescenceStatus.FLOWERING)
            or (
                p.florescence
                and any(
                    pp.ongoing
                    for pp in p.florescence.pollinations
                    # if pp.id != p.id  # exclude self
                )
            )
        ]
        n_successful = len(
            [
                p
                for p in pollinations
                if p.pollination_status != PollinationStatus.ATTEMPT and p.ongoing
            ]
        )
    else:
        assert year is not None and month is not None  # noqa
        period = f"{year}-{month}"
        pollinations = [
            p
            for p in pollinations
            if p.pollinated_at is not None
            and p.pollinated_at.year == year
            and p.pollinated_at.month == month
        ]
        n_successful = len(
            [p for p in pollinations if p.pollination_status != PollinationStatus.ATTEMPT]
        )

    results = []
    # we're ignoring initially  successful pollinations that were aborted for whatever reason (e.g. damage)
    n_failed = len(
        [
            p
            for p in pollinations
            if not p.ongoing and p.pollination_status == PollinationStatus.ATTEMPT
        ]
    )
    n_successful_and_failed = n_successful + n_failed
    quota_failed = round(
        n_failed / n_successful_and_failed * 100 if n_successful_and_failed > 0 else 0
    )
    if n_failed:
        results.append(
            PollinationStatisticsRow(
                period=period, label="Pollinations Failed", value=f"{n_failed} ({quota_failed}%)"
            )
        )
    quota_successful = round(
        n_successful / n_successful_and_failed * 100 if n_successful_and_failed > 0 else 0
    )
    if n_successful:
        results.append(
            PollinationStatisticsRow(
                period=period,
                label="Pollinations Successful",
                value=f"{n_successful} ({quota_successful}%)",
            )
        )

    n_still_open = len(
        [p for p in pollinations if p.ongoing and p.pollination_status == PollinationStatus.ATTEMPT]
    )
    if n_still_open > 0:
        results.append(
            PollinationStatisticsRow(
                period=period, label="Pollinations Still Open", value=f"{n_still_open}"
            )
        )
    return results


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

    all_pollinations = await pollination_dal.get_pollinations(
        include_ongoing_pollinations=True,
        include_recently_finished_pollinations=True,
        include_finished_pollinations=True,
    )

    results = compute_pollination_statistics_for_month(
        all_pollinations,
        recent=True,
    )

    today = datetime.date.today()
    for i in range(12):
        year = today.year if today.month - i > 0 else today.year - 1
        month = (today.month - i - 1) % 12 + 1
        results += compute_pollination_statistics_for_month(
            all_pollinations, year=year, month=month
        )

    return PollinationStatisticsRead(texts_tabular=results)

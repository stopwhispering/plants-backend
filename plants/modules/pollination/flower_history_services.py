from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import pytz

from plants.modules.pollination.enums import FlorescenceStatus, FloweringState
from plants.modules.pollination.schemas import FlowerHistoryRow

if TYPE_CHECKING:
    from plants.modules.plant.models import Plant
    from plants.modules.pollination.florescence_dal import FlorescenceDAL
    from plants.modules.pollination.models import Florescence

logger = logging.getLogger(__name__)

AVG_DURATION_INFLORESCENCE_TO_FIRST_FLOWER_OPENING = 38
AVG_DURATION_FIRST_TO_LAST_FLOWER = 18
AVG_DURATION_FIRST_FLOWER_TO_FIRST_SEED = 47
AVG_DURATION_FIRST_FLOWER_TO_LAST_SEED = 55
AVG_DURATION_INFLORESCENCE_TO_FIRST_FLOWER = 38
AVG_DURATION_FIRST_TO_LAST_SEED = 8


@dataclass
class FloweringPeriod:
    start: date
    start_verified: bool
    end: date
    end_verified: bool
    flowering_state: FloweringState

    def get_state_at_date(self, date_: date) -> FloweringState:
        if self.start <= date_ <= self.end:
            return self.flowering_state
        return FloweringState.NOT_FLOWERING


class FloweringPlant:
    def __init__(self, plant: Plant):
        self.plant = plant
        self.florescences: list[Florescence] = plant.florescences
        self.periods: list[FloweringPeriod] = []

        for florescence in self.florescences:
            if period := self._get_inflorescence_period(florescence):
                self.periods.append(period)
            if period := self._get_flowering_period(florescence):
                self.periods.append(period)
            if period := self._get_seed_ripening_period(florescence):
                self.periods.append(period)

    def has_any_valid_period(self) -> bool:
        return any(self.periods)

    def get_earliest_period_start(self) -> date:
        return min(period.start for period in self.periods)

    def get_state_at_date(self, date_: date) -> FloweringState:
        states = [period.get_state_at_date(date_) for period in self.periods]
        if FloweringState.FLOWERING in states:
            return FloweringState.FLOWERING
        if FloweringState.SEEDS_RIPENING in states:
            return FloweringState.SEEDS_RIPENING
        if FloweringState.INFLORESCENCE_GROWING in states:
            return FloweringState.INFLORESCENCE_GROWING
        return FloweringState.NOT_FLOWERING

    def _get_inflorescence_period(self, florescence: Florescence) -> FloweringPeriod | None:
        # simple case - inflorescence period is known
        if florescence.inflorescence_appeared_at and florescence.first_flower_opened_at:
            return FloweringPeriod(
                start=florescence.inflorescence_appeared_at,
                start_verified=True,
                end=florescence.first_flower_opened_at - timedelta(days=1),
                end_verified=True,
                flowering_state=FloweringState.INFLORESCENCE_GROWING,
            )

        # start is known, end is not
        if florescence.inflorescence_appeared_at and not florescence.first_flower_opened_at:
            if florescence.last_flower_closed_at:
                estimated_first_flower_date = florescence.last_flower_closed_at - timedelta(
                    days=AVG_DURATION_FIRST_TO_LAST_FLOWER
                )
            elif florescence.first_seed_ripening_date:
                estimated_first_flower_date = florescence.first_seed_ripening_date - timedelta(
                    days=AVG_DURATION_FIRST_FLOWER_TO_FIRST_SEED
                )
            elif florescence.last_seed_ripening_date:
                estimated_first_flower_date = florescence.last_seed_ripening_date - timedelta(
                    days=AVG_DURATION_FIRST_FLOWER_TO_LAST_SEED
                )
            else:
                logger.debug(
                    f"Abandoned inflorescence {florescence.id} for plant "
                    f"{self.plant.plant_name}"
                )
                return None

            return FloweringPeriod(
                start=florescence.inflorescence_appeared_at,
                start_verified=True,
                end=estimated_first_flower_date - timedelta(days=1),
                end_verified=False,
                flowering_state=FloweringState.INFLORESCENCE_GROWING,
            )

        # end date is known, start is not
        if florescence.first_flower_opened_at:
            return FloweringPeriod(
                start=(
                    florescence.first_flower_opened_at
                    - timedelta(days=AVG_DURATION_INFLORESCENCE_TO_FIRST_FLOWER)
                ),
                start_verified=False,
                end=florescence.first_flower_opened_at - timedelta(days=1),
                end_verified=True,
                flowering_state=FloweringState.INFLORESCENCE_GROWING,
            )

        logger.warning(
            f"Can't determine inflorescence period - Unknown dates for "
            f"{florescence.plant.plant_name}. Comment: {florescence.comment}"
        )
        return None

    def _get_flowering_period(self, florescence: Florescence) -> FloweringPeriod | None:
        # simple case - start and end dates are known
        if florescence.first_flower_opened_at and florescence.last_flower_closed_at:
            return FloweringPeriod(
                start=florescence.first_flower_opened_at,
                start_verified=True,
                # florescence.last_flower_closed_at - timedelta(days=1),
                end=florescence.last_flower_closed_at,
                end_verified=True,
                flowering_state=FloweringState.FLOWERING,
            )

        # start is known, end is not but flower is still ongoing
        # in that case we'll set the end date to current date
        if (
            florescence.first_flower_opened_at
            and not florescence.last_flower_closed_at
            and florescence.florescence_status == FlorescenceStatus.FLOWERING
        ):
            return FloweringPeriod(
                start=florescence.first_flower_opened_at,
                start_verified=True,
                end=datetime.now(tz=pytz.timezone("Europe/Berlin")).date(),
                # end=date.today(),
                end_verified=False,
                flowering_state=FloweringState.FLOWERING,
            )

        # start is known, end is not
        if florescence.first_flower_opened_at and not florescence.last_flower_closed_at:
            if florescence.first_seed_ripening_date:
                estimated_last_flower_date = florescence.first_seed_ripening_date - timedelta(
                    days=AVG_DURATION_FIRST_FLOWER_TO_FIRST_SEED
                )
            elif florescence.last_seed_ripening_date:
                estimated_last_flower_date = florescence.last_seed_ripening_date - timedelta(
                    days=AVG_DURATION_FIRST_FLOWER_TO_LAST_SEED
                )
            else:
                logger.warning(
                    f"Abandoned flowering {florescence.id} for plant " f"{self.plant.plant_name}"
                )
                return None

            return FloweringPeriod(
                start=florescence.first_flower_opened_at,
                start_verified=True,
                end=estimated_last_flower_date - timedelta(days=1),
                end_verified=False,
                flowering_state=FloweringState.FLOWERING,
            )

        # end date is known, start is not
        if florescence.last_flower_closed_at:
            return FloweringPeriod(
                start=(
                    florescence.last_flower_closed_at
                    - timedelta(days=AVG_DURATION_FIRST_TO_LAST_FLOWER)
                ),
                start_verified=False,
                end=florescence.last_flower_closed_at - timedelta(days=1),
                end_verified=True,
                flowering_state=FloweringState.FLOWERING,
            )

        return None

    def _get_seed_ripening_period(self, florescence: Florescence) -> FloweringPeriod | None:
        # beginning is estimated to be inbetween first and last flower
        calculated_start: date | None
        if florescence.first_flower_opened_at and florescence.last_flower_closed_at:
            calculated_start = (
                florescence.first_flower_opened_at
                + (florescence.last_flower_closed_at - florescence.first_flower_opened_at) / 2
            )
        else:
            calculated_start = None

        # simple case - start and end dates are known
        if calculated_start and florescence.last_seed_ripening_date:
            return FloweringPeriod(
                start=calculated_start,
                start_verified=True,  # !
                end=florescence.last_seed_ripening_date,
                end_verified=True,
                flowering_state=FloweringState.SEEDS_RIPENING,
            )

        # start is known, end is not
        if calculated_start:
            if florescence.first_seed_ripening_date:
                estimated_last_seed_date = florescence.first_seed_ripening_date + timedelta(
                    days=AVG_DURATION_FIRST_TO_LAST_SEED
                )
            else:
                logger.warning(
                    f"Abandoned seed ripening {florescence.id} for plant "
                    f"{self.plant.plant_name}"
                )
                return None
            return FloweringPeriod(
                start=calculated_start,
                start_verified=True,  # !
                end=estimated_last_seed_date,
                end_verified=False,
                flowering_state=FloweringState.SEEDS_RIPENING,
            )

        # end is known, start is not
        if florescence.last_seed_ripening_date:
            return FloweringPeriod(
                start=(
                    florescence.last_seed_ripening_date
                    - timedelta(days=AVG_DURATION_FIRST_TO_LAST_SEED)
                ),
                start_verified=False,
                end=florescence.last_seed_ripening_date,
                end_verified=True,
                flowering_state=FloweringState.SEEDS_RIPENING,
            )

        logger.debug(
            f"Can't determine seed ripening period - Unknown dates for "
            f"{florescence.plant.plant_name}. "
            f"Comment: {florescence.comment}"
        )
        return None


def _populate_flowering_plants(distinct_plants: set[Plant]) -> list[FloweringPlant]:
    flowering_plants = []
    for plant in distinct_plants:
        flowering_plant = FloweringPlant(plant)
        if flowering_plant.has_any_valid_period():
            flowering_plants.append(flowering_plant)
    return flowering_plants


async def generate_flower_history(
    florescence_dal: FlorescenceDAL, plant: Plant | None = None, *, include_inactive_plants: bool
) -> list[FlowerHistoryRow]:
    """If plant is supplied, the flower history is generated only for that plant, otherwise for all
    plants."""
    if plant:
        distinct_plants = {plant}

    else:
        florescences = await florescence_dal.get_all_florescences(
            include_inactive_plants=include_inactive_plants
        )
        distinct_plants = {f.plant for f in florescences} if not plant else {plant}

    flowering_plants: list[FloweringPlant] = _populate_flowering_plants(distinct_plants)
    if not flowering_plants:
        return []

    flowering_plants.sort(key=lambda fp: fp.plant.plant_name)

    flower_history_rows: list[FlowerHistoryRow] = []
    flowering_plant: FloweringPlant
    for flowering_plant in flowering_plants:
        # consider years from first flower to current year
        years = list(
            range(
                flowering_plant.get_earliest_period_start().year,
                datetime.now(tz=pytz.timezone("CET")).year + 1,
            )
        )

        for year in years:
            flower_history_rows.append(
                FlowerHistoryRow(
                    plant_id=flowering_plant.plant.id,
                    plant_name=flowering_plant.plant.plant_name,
                    year=str(year),
                    month_01=flowering_plant.get_state_at_date(date(year, 1, 15)),
                    month_02=flowering_plant.get_state_at_date(date(year, 2, 15)),
                    month_03=flowering_plant.get_state_at_date(date(year, 3, 15)),
                    month_04=flowering_plant.get_state_at_date(date(year, 4, 15)),
                    month_05=flowering_plant.get_state_at_date(date(year, 5, 15)),
                    month_06=flowering_plant.get_state_at_date(date(year, 6, 15)),
                    month_07=flowering_plant.get_state_at_date(date(year, 7, 15)),
                    month_08=flowering_plant.get_state_at_date(date(year, 8, 15)),
                    month_09=flowering_plant.get_state_at_date(date(year, 9, 15)),
                    month_10=flowering_plant.get_state_at_date(date(year, 10, 15)),
                    month_11=flowering_plant.get_state_at_date(date(year, 11, 15)),
                    month_12=flowering_plant.get_state_at_date(date(year, 12, 15)),
                )
            )

    return flower_history_rows

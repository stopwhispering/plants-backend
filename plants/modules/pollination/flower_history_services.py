import logging
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from dateutil import rrule

from sqlalchemy.orm import Session

from plants.modules.plant.models import Plant
from plants.modules.pollination.models import Florescence, BFlorescenceStatus
from plants.util.ui_utils import FORMAT_YYYY_MM
from plants.modules.pollination.schemas import BFloweringState, BPlantFlowerHistory

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
    flowering_state: BFloweringState

    def get_state_at_date(self, date: date) -> BFloweringState:
        if self.start <= date <= self.end:
            return self.flowering_state
        else:
            return BFloweringState.NOT_FLOWERING


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
        return min([period.start for period in self.periods])

    def get_state_at_date(self, date: date) -> BFloweringState:
        states = [period.get_state_at_date(date) for period in self.periods]
        if BFloweringState.FLOWERING in states:
            return BFloweringState.FLOWERING
        elif BFloweringState.SEEDS_RIPENING in states:
            return BFloweringState.SEEDS_RIPENING
        elif BFloweringState.INFLORESCENCE_GROWING in states:
            return BFloweringState.INFLORESCENCE_GROWING
        else:
            return BFloweringState.NOT_FLOWERING

    def _get_inflorescence_period(self, florescence: Florescence) -> FloweringPeriod | None:
        # simple case - inflorescence period is known
        if florescence.inflorescence_appearance_date and florescence.first_flower_opening_date:
            return FloweringPeriod(
                start=florescence.inflorescence_appearance_date,
                start_verified=True,
                end=florescence.first_flower_opening_date - timedelta(days=1),
                end_verified=True,
                flowering_state=BFloweringState.INFLORESCENCE_GROWING
            )

        # start is known, end is not
        elif florescence.inflorescence_appearance_date and not florescence.first_flower_opening_date:
            if florescence.last_flower_closing_date:
                estimated_first_flower_date = (florescence.last_flower_closing_date -
                                               timedelta(days=AVG_DURATION_FIRST_TO_LAST_FLOWER))
            elif florescence.first_seed_ripening_date:
                estimated_first_flower_date = (florescence.first_seed_ripening_date -
                                               timedelta(days=AVG_DURATION_FIRST_FLOWER_TO_FIRST_SEED))
            elif florescence.last_seed_ripening_date:
                estimated_first_flower_date = (florescence.last_seed_ripening_date -
                                               timedelta(days=AVG_DURATION_FIRST_FLOWER_TO_LAST_SEED))
            else:
                logger.warning(f'Abandoned inflorescence {florescence.id} for plant {self.plant.plant_name}')
                return None

            return FloweringPeriod(
                start=florescence.inflorescence_appearance_date,
                start_verified=True,
                end=estimated_first_flower_date - timedelta(days=1),
                end_verified=False,
                flowering_state=BFloweringState.INFLORESCENCE_GROWING
            )

        # end date is known, start is not
        elif florescence.first_flower_opening_date:
            return FloweringPeriod(
                start=(florescence.first_flower_opening_date -
                       timedelta(days=AVG_DURATION_INFLORESCENCE_TO_FIRST_FLOWER)),
                start_verified=False,
                end=florescence.first_flower_opening_date - timedelta(days=1),
                end_verified=True,
                flowering_state=BFloweringState.INFLORESCENCE_GROWING
            )

        else:
            logger.warning(f"Can't determine inflorescence period - Unknown dates for {florescence.plant.plant_name}. "
                           f"Comment: {florescence.comment}")
            return None

    def _get_flowering_period(self, florescence: Florescence) -> FloweringPeriod | None:
        # simple case - start and end dates are known
        if florescence.first_flower_opening_date and florescence.last_flower_closing_date:
            return FloweringPeriod(
                start=florescence.first_flower_opening_date,
                start_verified=True,
                end=florescence.last_flower_closing_date - timedelta(days=1),
                end_verified=True,
                flowering_state=BFloweringState.FLOWERING
            )

        # start is known, end is not
        elif florescence.first_flower_opening_date and not florescence.last_flower_closing_date:
            if florescence.first_seed_ripening_date:
                estimated_last_flower_date = (florescence.first_seed_ripening_date -
                                              timedelta(days=AVG_DURATION_FIRST_FLOWER_TO_FIRST_SEED))
            elif florescence.last_seed_ripening_date:
                estimated_last_flower_date = (florescence.last_seed_ripening_date -
                                              timedelta(days=AVG_DURATION_FIRST_FLOWER_TO_LAST_SEED))
            else:
                logger.warning(f'Abandoned flowering {florescence.id} for plant {self.plant.plant_name}')
                return None

            return FloweringPeriod(
                start=florescence.first_flower_opening_date,
                start_verified=True,
                end=estimated_last_flower_date - timedelta(days=1),
                end_verified=False,
                flowering_state=BFloweringState.FLOWERING
            )

        # end date is known, start is not
        elif florescence.last_flower_closing_date:
            return FloweringPeriod(
                start=(florescence.last_flower_closing_date -
                       timedelta(days=AVG_DURATION_FIRST_TO_LAST_FLOWER)),
                start_verified=False,
                end=florescence.last_flower_closing_date - timedelta(days=1),
                end_verified=True,
                flowering_state=BFloweringState.FLOWERING
            )
        else:
            logger.warning(f"Can't determine flowering period - Unknown dates for {florescence.plant.plant_name}. "
                           f"Comment: {florescence.comment}")

    def _get_seed_ripening_period(self, florescence: Florescence) -> FloweringPeriod | None:

        # beginning is estimated to be inbetween first and last flower
        calculated_start: date | None
        if florescence.first_flower_opening_date and florescence.last_flower_closing_date:
            calculated_start = florescence.first_flower_opening_date + (
                    florescence.last_flower_closing_date - florescence.first_flower_opening_date
            ) / 2
        else:
            calculated_start = None

        # simple case - start and end dates are known
        if calculated_start and florescence.last_seed_ripening_date:
            return FloweringPeriod(
                start=calculated_start,
                start_verified=True,  # !
                end=florescence.last_seed_ripening_date,
                end_verified=True,
                flowering_state=BFloweringState.SEEDS_RIPENING
            )

        # start is known, end is not
        elif calculated_start:
            if florescence.first_seed_ripening_date:
                estimated_last_seed_date = (florescence.first_seed_ripening_date
                                            + timedelta(days=AVG_DURATION_FIRST_TO_LAST_SEED))
            else:
                logger.warning(f'Abandoned seed ripening {florescence.id} for plant {self.plant.plant_name}')
                return None
            return FloweringPeriod(
                start=calculated_start,
                start_verified=True,  # !
                end=estimated_last_seed_date,
                end_verified=False,
                flowering_state=BFloweringState.SEEDS_RIPENING
            )

        # end is known, start is not
        elif florescence.last_seed_ripening_date:
            return FloweringPeriod(
                start=(florescence.last_seed_ripening_date -
                       timedelta(days=AVG_DURATION_FIRST_TO_LAST_SEED)),
                start_verified=False,
                end=florescence.last_seed_ripening_date,
                end_verified=True,
                flowering_state=BFloweringState.SEEDS_RIPENING
            )

        else:
            logger.warning(f"Can't determine seed ripening period - Unknown dates for {florescence.plant.plant_name}. "
                           f"Comment: {florescence.comment}")
            return None


def _populate_flowering_plants(distinct_plants: set[Plant]) -> list[FloweringPlant]:
    flowering_plants = []
    for plant in distinct_plants:
        flowering_plant = FloweringPlant(plant)
        if flowering_plant.has_any_valid_period():
            flowering_plants.append(flowering_plant)
    return flowering_plants


def generate_flower_history(db: Session):
    florescences = db.query(Florescence).filter(
        Florescence.florescence_status == BFlorescenceStatus.FINISHED.value).all()
    distinct_plants = set([f.plant for f in florescences])
    flowering_plants: list[FloweringPlant] = _populate_flowering_plants(distinct_plants)

    # sort by first period start ascending
    flowering_plants.sort(key=lambda fp: fp.get_earliest_period_start())
    earliest_date = flowering_plants[0].get_earliest_period_start()

    # # for each month (between earliest_date and today) and plant, get the flowering
    # # state with highest priority (flowering > seeds ripening > inflorescence)
    # plant_to_periods: dict[str, dict[date, BFloweringState]] = {}
    # for fp in flowering_plants:
    #     period_to_status: dict[date, BFloweringState] = {}
    #     for month in rrule.rrule(rrule.MONTHLY, dtstart=earliest_date, until=date.today()):
    #         month: datetime
    #         status: BFloweringState = fp.get_state_at_date(month.date())
    #         period_to_status[month.date()] = status
    #     plant_to_periods[fp.plant.plant_name] = period_to_status

    # for fp in flowering_plants:
    #
    datetimes: list[datetime] = list(rrule.rrule(rrule.MONTHLY, dtstart=earliest_date, until=date.today()))
    months = [d.strftime(FORMAT_YYYY_MM) for d in datetimes]

    flower_history = []
    for fp in flowering_plants:
        fp: FloweringPlant
        plant_flower_history = {
            'plant_id': fp.plant.id,
            'plant_name': fp.plant.plant_name,
            'periods': [],
        }
        for dt in datetimes:
            plant_flower_history['periods'].append({
                'month': dt.strftime(FORMAT_YYYY_MM),
                'flowering_state': fp.get_state_at_date(dt.date())
            })
        BPlantFlowerHistory.validate(plant_flower_history)
        flower_history.append(plant_flower_history)

    return months, flower_history

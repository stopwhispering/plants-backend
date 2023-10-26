from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
import pytz

from plants.modules.pollination.enums import (
    BFloweringState,
    Context,
    FlorescenceStatus,
    FlowerColorDifferentiation,
    Location,
    PollenQuality,
    PollenType,
    PollinationStatus,
    StigmaPosition,
)
from plants.modules.pollination.flower_history_services import FloweringPlant
from plants.modules.pollination.models import Florescence, Pollination

if TYPE_CHECKING:
    from plants.modules.plant.models import Plant


@pytest.mark.asyncio()
async def test_florescence_history_without_pollination(
    plant_valid_with_active_florescence_in_db: Plant,
) -> None:
    plant = plant_valid_with_active_florescence_in_db

    # add some florescence into the plant's history
    florescence_without_pollination = Florescence(
        plant_id=plant.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second="#ffdd00",
        flower_colors_differentiation=FlowerColorDifferentiation.OVARY_MOUTH,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=FlorescenceStatus.FINISHED,
        inflorescence_appeared_at=datetime.date(2021, 3, 1),
        first_flower_opened_at=datetime.date(2021, 5, 1),
        last_flower_closed_at=datetime.date(2021, 6, 1),
        creation_context=Context.API,
    )
    plant.florescences.append(florescence_without_pollination)

    flowering_plant = FloweringPlant(plant)

    # inflorescence
    inflorescence_period = next(
        p for p in flowering_plant.periods if p.start == datetime.date(2021, 3, 1)
    )
    assert inflorescence_period.flowering_state == BFloweringState.INFLORESCENCE_GROWING
    # end must be one day before next period start
    assert inflorescence_period.end == datetime.date(2021, 4, 30)

    # florescence
    florescence_period = next(
        p for p in flowering_plant.periods if p.start == datetime.date(2021, 5, 1)
    )
    assert florescence_period.flowering_state == BFloweringState.FLOWERING
    # end must be the day the last flower closed
    assert florescence_period.end == datetime.date(2021, 6, 1)


@pytest.mark.asyncio()
async def test_florescence_history_still_active(
    plant_valid_with_active_florescence_in_db: Plant,
) -> None:
    """Difference to test_florescence_history_without_pollination: florescence is still ongoing, we
    expect the last period to end at the current date."""
    plant = plant_valid_with_active_florescence_in_db

    # add some florescence into the plant's history
    florescence = Florescence(
        plant_id=plant.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second="#ffdd00",
        flower_colors_differentiation=FlowerColorDifferentiation.OVARY_MOUTH,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=FlorescenceStatus.FLOWERING,
        inflorescence_appeared_at=datetime.date(2021, 3, 1),
        first_flower_opened_at=datetime.date(2021, 5, 1),
        last_flower_closed_at=None,  # still flowering!
        creation_context=Context.API,
    )
    plant.florescences.append(florescence)

    flowering_plant = FloweringPlant(plant)

    # florescence still ongoing
    florescence_period = next(
        p for p in flowering_plant.periods if p.start == datetime.date(2021, 5, 1)
    )
    assert florescence_period.flowering_state == BFloweringState.FLOWERING
    # end must be the current date
    assert florescence_period.end == datetime.datetime.now(tz=pytz.timezone("Europe/Berlin")).date()


@pytest.mark.asyncio()
async def test_florescence_history_with_pollination(
    plant_valid_with_active_florescence_in_db: Plant,
    another_valid_plant_in_db: Plant,
) -> None:
    plant = plant_valid_with_active_florescence_in_db

    pollination_1 = Pollination(
        seed_capsule_plant_id=plant.id,
        pollen_donor_plant_id=another_valid_plant_in_db.id,
        pollen_type=PollenType.FROZEN,
        pollen_quality=PollenQuality.GOOD,
        location=Location.INDOOR,
        creation_at_context=Context.API,
        pollination_status=PollinationStatus.GERMINATED,
        ongoing=False,
    )

    # add some florescence into the plant's history
    florescence_with_pollination = Florescence(
        plant_id=plant.id,
        flowers_count=10,
        perianth_length=Decimal(1.9),
        perianth_diameter=Decimal(0.8),
        flower_color="#f2f600",
        flower_color_second="#ffdd00",
        flower_colors_differentiation=FlowerColorDifferentiation.OVARY_MOUTH,
        stigma_position=StigmaPosition.DEEPLY_INSERTED,
        florescence_status=FlorescenceStatus.FLOWERING,
        inflorescence_appeared_at=datetime.date(2021, 3, 1),
        first_flower_opened_at=datetime.date(2021, 5, 1),
        last_flower_closed_at=datetime.date(2021, 6, 1),
        last_seed_ripening_date=datetime.date(2021, 7, 1),
        creation_context=Context.API,
        pollinations=[pollination_1],
    )
    plant.florescences.append(florescence_with_pollination)

    flowering_plant = FloweringPlant(plant)

    # inflorescence
    inflorescence_period = next(
        p for p in flowering_plant.periods if p.start == datetime.date(2021, 3, 1)
    )
    assert inflorescence_period.flowering_state == BFloweringState.INFLORESCENCE_GROWING
    # end must be one day before next period start
    assert inflorescence_period.end == datetime.date(2021, 4, 30)

    # florescence
    florescence_period = next(
        p for p in flowering_plant.periods if p.start == datetime.date(2021, 5, 1)
    )
    assert florescence_period.flowering_state == BFloweringState.FLOWERING
    # end must be the day the last flower closed
    assert florescence_period.end == datetime.date(2021, 6, 1)

    # pollination start date must be calculated as the middle of the florescence
    pollination_period = next(
        p for p in flowering_plant.periods if p.start == datetime.date(2021, 5, 16)
    )
    # pollination_period = [
    #     p for p in flowering_plant.periods if p.start == datetime.date(2021, 5, 16)
    # ][0]
    assert pollination_period.flowering_state == BFloweringState.SEEDS_RIPENING
    assert pollination_period.end == datetime.date(2021, 7, 1)

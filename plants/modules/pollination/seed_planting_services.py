from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytz
from dateutil.relativedelta import relativedelta

from plants.modules.pollination.enums import SeedPlantingStatus
from plants.modules.pollination.models import SeedPlanting

if TYPE_CHECKING:
    from plants.modules.pollination.schemas import SeedPlantingCreate, SeedPlantingUpdate
    from plants.modules.pollination.seed_planting_dal import SeedPlantingDAL


async def read_active_seed_plantings(
    seed_planting_dal: SeedPlantingDAL,
) -> list[SeedPlanting]:
    """Read all active seed plantings, i.e. seed plantings that have not been abandoned, yet, or
    that germinated not too long ago."""
    seed_plantings = await seed_planting_dal.by_status(
        {SeedPlantingStatus.PLANTED, SeedPlantingStatus.GERMINATED}
    )

    one_week_ago = (datetime.now(tz=pytz.utc) - relativedelta(days=7)).date()
    return [
        s
        for s in seed_plantings
        if s.status == SeedPlantingStatus.PLANTED
        or (s.status == SeedPlantingStatus.GERMINATED)
        and s.germinated_first_on is not None  # for mypy
        and s.germinated_first_on >= one_week_ago
    ]


async def save_new_seed_planting(
    new_seed_planting_data: SeedPlantingCreate,
    seed_planting_dal: SeedPlantingDAL,
) -> None:
    """Save a new seed planting."""
    new_seed_planting = SeedPlanting(
        status=SeedPlantingStatus.PLANTED,
        pollination_id=new_seed_planting_data.pollination_id,
        comment=new_seed_planting_data.comment,
        sterilized=new_seed_planting_data.sterilized,
        soaked=new_seed_planting_data.soaked,
        planted_on=new_seed_planting_data.planted_on,  # todo convert?
        count_planted=new_seed_planting_data.count_planted,
    )
    await seed_planting_dal.create(new_seed_planting)


async def update_seed_planting(
    seed_planting: SeedPlanting,
    edited_seed_planting_data: SeedPlantingUpdate,
    seed_planting_dal: SeedPlantingDAL,
) -> None:
    """Update db record of a seed planting."""
    updates = edited_seed_planting_data.dict(exclude={})
    await seed_planting_dal.update(seed_planting, updates=updates)


async def remove_seed_planting(
    seed_planting: SeedPlanting, seed_planting_dal: SeedPlantingDAL
) -> None:
    """Delete a seed planting from db."""
    await seed_planting_dal.delete(seed_planting)

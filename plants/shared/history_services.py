from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pytz

if TYPE_CHECKING:
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.shared.history_dal import HistoryDAL

from plants.shared.history_models import History


async def create_history_entry(
    description: str,
    history_dal: HistoryDAL,
    plant_dal: PlantDAL,
    plant_id: int | None = None,
    plant_name: str | None = None,
) -> None:
    if not plant_name:
        if not plant_id:
            raise ValueError("Neither Plant ID nor Name provided.")
        plant_name = await plant_dal.get_name_by_id(plant_id)
    if not plant_id:
        if not plant_name:
            raise ValueError("Neither Plant ID nor Name provided.")
        plant_id = await plant_dal.get_id_by_name(plant_name)

    entry = History(
        timestamp=datetime.datetime.now(tz=pytz.utc),
        plant_id=plant_id,
        plant_name=plant_name,
        description=description,
    )

    await history_dal.create(entry)

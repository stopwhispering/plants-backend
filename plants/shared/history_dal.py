from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pytz
from sqlalchemy import select

from plants.shared.base_dal import BaseDAL
from plants.shared.history_models import History

if TYPE_CHECKING:
    from plants.modules.plant.models import Plant


class HistoryDAL(BaseDAL):
    async def create_entry(self, plant: Plant, description: str) -> None:
        entry = History(
            timestamp=datetime.datetime.now(tz=pytz.utc),
            plant_id=plant.id,
            plant_name=plant.plant_name,
            description=description,
        )
        self.session.add(entry)
        await self.session.flush()

    async def get_all(self) -> list[History]:
        query = select(History)
        return list((await self.session.scalars(query)).all())

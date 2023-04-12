from __future__ import annotations

from sqlalchemy import select

from plants.shared.base_dal import BaseDAL
from plants.shared.history_models import History


class HistoryDAL(BaseDAL):
    async def create(self, history: History) -> None:
        self.session.add(history)
        await self.session.flush()

    async def get_all(self) -> list[History]:
        query = select(History)
        return list((await self.session.scalars(query)).all())

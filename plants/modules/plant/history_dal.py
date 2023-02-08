from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from plants.shared.base_dal import BaseDAL
from plants.shared.history_models import History


class HistoryDAL(BaseDAL):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, history: History):
        self.session.add(history)
        await self.session.flush()

    async def get_all(self):
        query = select(History)
        history = (await self.session.scalars(query)).all()
        return history

from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAL(object):
    def __init__(self, session: AsyncSession):
        self.session = session

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class BaseDAL(object):
    def __init__(self, session: AsyncSession):
        self.session = session

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAL:
    def __init__(self, session: AsyncSession):
        self.session = session

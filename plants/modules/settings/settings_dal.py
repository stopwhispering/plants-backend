from __future__ import annotations

from sqlalchemy import select
from plants.modules.settings.models import Settings
from plants.shared.base_dal import BaseDAL


class SettingsDAL(BaseDAL):

    async def get_settings(self) -> list[Settings]:
        query = select(Settings)
        settings: list[Settings] = list((await self.session.scalars(query)).all())
        return settings

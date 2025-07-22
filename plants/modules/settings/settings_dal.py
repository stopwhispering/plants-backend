from __future__ import annotations

from typing import Any

from sqlalchemy import select

from plants.modules.settings.models import Settings
from plants.shared.base_dal import BaseDAL


class SettingsDAL(BaseDAL):
    async def get_settings(self) -> list[Settings]:
        query = select(Settings)
        settings: list[Settings] = list((await self.session.scalars(query)).all())
        return settings

    async def update_settings(self, settings: dict[str, Any]) -> None:
        for key, value in settings.items():
            query = select(Settings).where(Settings.key == key)
            existing_setting: Settings | None = await self.session.scalar(query)
            existing_setting.value = value
        await self.session.commit()

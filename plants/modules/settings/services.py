from __future__ import annotations

from typing import TYPE_CHECKING

from plants.exceptions import NotValidDaysError
from plants.modules.settings.schemas import SettingsBase, SettingsRead

if TYPE_CHECKING:
    from plants.modules.settings.settings_dal import SettingsDAL


async def read_settings(settings_dal: SettingsDAL) -> SettingsRead:
    """Read settings from settings table."""
    all_settings = await settings_dal.get_settings()

    return SettingsRead(
        last_image_warning_after_n_days=int(
            next(s.value for s in all_settings if s.key == "last_image_warning_after_n_days")
        )
    )


async def save_settings(settings: SettingsBase, settings_dal: SettingsDAL) -> None:
    """Save updated settings; all settings are supplied, no matter whether changed or not."""
    settings_dict = settings.model_dump(exclude={})

    if not (1 <= settings_dict["last_image_warning_after_n_days"] <= 999):
        raise NotValidDaysError
    settings_dict["last_image_warning_after_n_days"] = str(
        settings_dict["last_image_warning_after_n_days"]
    )

    await settings_dal.update_settings(settings_dict)

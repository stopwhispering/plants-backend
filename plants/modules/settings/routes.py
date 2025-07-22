from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from plants.dependencies import get_settings_dal
from plants.modules.settings.schemas import (
    GetSettingsResponse,
    UpdateSettingsRequest,
    UpdateSettingsResponse,
)
from plants.modules.settings.services import read_settings, save_settings
from plants.modules.settings.settings_dal import SettingsDAL
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=GetSettingsResponse)
async def get_settings(settings_dal: SettingsDAL = Depends(get_settings_dal)) -> Any:
    """Read settings from settings table."""
    settings = await read_settings(settings_dal)
    return {
        "action": "Get settings",
        "message": get_message("Loaded settings from database."),
        "settings": settings,
    }


@router.put("/", response_model=UpdateSettingsResponse)
async def update_settings(
    data: UpdateSettingsRequest, settings_dal: SettingsDAL = Depends(get_settings_dal)
) -> Any:
    """Save updated settings; all settings are supplied, no matter whether changed or not."""
    await save_settings(data.settings, settings_dal)

    settings = await read_settings(settings_dal)
    return {
        "action": "Update settings",
        "message": get_message("Updated settings in database."),
        "settings": settings,
    }

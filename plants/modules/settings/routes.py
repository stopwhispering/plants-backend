
import logging

from fastapi import APIRouter, Depends

from typing import Any

from plants.dependencies import get_settings_dal
from plants.modules.settings.schemas import GetSettingsResponse, DisplaySettingsRead
from plants.modules.settings.settings_dal import SettingsDAL
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=GetSettingsResponse)
async def get_plants(plant_dal: SettingsDAL = Depends(get_settings_dal)) -> Any:
    """Read settings from settings table; since no logic is required except for dtype conversion,
    we don't use a separate service module."""
    all_settings = await plant_dal.get_settings()

    display_settings = DisplaySettingsRead(
        last_image_warning_after_n_days=int(next(
            (s.value for s in all_settings if s.key == "last_image_warning_after_n_days")
        ))
    )
    return {
        "action": "Get settings",
        "message": get_message("Loaded settings from database."),
        "display_settings": display_settings,
    }

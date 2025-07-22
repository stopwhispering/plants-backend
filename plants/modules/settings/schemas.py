from __future__ import annotations

from plants.shared.base_schema import (
    BaseSchema,
    ResponseContainer,
)


class SettingsBase(BaseSchema):
    last_image_warning_after_n_days: int


class UpdateSettingsRequest(BaseSchema):
    settings: SettingsBase


class SettingsRead(SettingsBase):
    last_updated_at: str | None = None


class GetSettingsResponse(ResponseContainer):
    settings: SettingsRead


class UpdateSettingsResponse(GetSettingsResponse):
    pass

from plants.shared.base_schema import (
    ResponseContainer, BaseSchema,
)


class DisplaySettingsBase(BaseSchema):
    last_image_warning_after_n_days: int


class DisplaySettingsRead(DisplaySettingsBase):
    last_updated_at: str | None = None


class GetSettingsResponse(ResponseContainer):
    display_settings: DisplaySettingsRead

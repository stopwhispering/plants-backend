from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from plants.shared.enums import MajorResource
from plants.shared.message_schemas import BMessage


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True, extra="ignore")


class ResponseContainer(BaseModel):
    action: str | None = None
    message: BMessage

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class MajorResponseContainer(ResponseContainer):
    resource: MajorResource


class RequestContainer(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

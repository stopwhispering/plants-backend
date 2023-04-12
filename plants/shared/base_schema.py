from __future__ import annotations

from pydantic import BaseModel, Extra

from plants.shared.enums import MajorResource
from plants.shared.message_schemas import BMessage


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True
        anystr_strip_whitespace = True
        extra = Extra.ignore


class ResponseContainer(BaseModel):
    action: str | None
    message: BMessage

    class Config:
        anystr_strip_whitespace = True
        extra = Extra.forbid


class MajorResponseContainer(ResponseContainer):
    resource: MajorResource


class RequestContainer(BaseModel):
    class Config:
        anystr_strip_whitespace = True
        extra = Extra.forbid

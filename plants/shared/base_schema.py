from typing import Optional

from pydantic import BaseModel, Extra

from plants.shared.enums import FBMajorResource
from plants.shared.message_schemas import BMessage


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True
        anystr_strip_whitespace = True
        extra = Extra.forbid


class ResponseContainer(BaseModel):
    action: Optional[str]
    message: BMessage

    class Config:
        anystr_strip_whitespace = True
        extra = Extra.forbid


class MajorResponseContainer(ResponseContainer):
    resource: FBMajorResource


class RequestContainer(BaseModel):
    class Config:
        anystr_strip_whitespace = True
        extra = Extra.forbid

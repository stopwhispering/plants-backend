from typing import Optional

from pydantic import Extra
from pydantic.main import BaseModel

from plants.shared.enums import MessageType, MajorResource


class BMessage(BaseModel):
    type: MessageType
    message: str
    additionalText: Optional[str]
    description: Optional[str]

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class BConfirmation(BaseModel):
    action: str
    message: BMessage

    class Config:
        extra = Extra.forbid


class BSaveConfirmation(BaseModel):
    """For the major resources (plants, images, taxa, events, we need to return the
    updated resource to the frontend to enable the frontend to identify when all
    resources have been saved."""

    resource: MajorResource
    message: BMessage

    class Config:
        use_enum_values = True
        extra = Extra.forbid

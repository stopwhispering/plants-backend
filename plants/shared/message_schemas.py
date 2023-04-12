from __future__ import annotations

from pydantic import Extra
from pydantic.main import BaseModel

from plants.shared.enums import MajorResource, MessageType


class BMessage(BaseModel):
    type: MessageType  # noqa: A003
    message: str
    description: str | None

    class Config:
        extra = Extra.forbid


class BConfirmation(BaseModel):
    action: str
    message: BMessage

    class Config:
        extra = Extra.forbid


class BSaveConfirmation(BaseModel):
    """For the major resources (plants, images, taxa, events, we need to return the updated resource
    to the frontend to enable the frontend to identify when all resources have been saved."""

    resource: MajorResource
    message: BMessage

    class Config:
        extra = Extra.forbid

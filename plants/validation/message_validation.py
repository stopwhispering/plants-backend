from typing import Optional

from pydantic import Extra
from pydantic.main import BaseModel

from plants.util.ui_utils import MessageType


class PMessage(BaseModel):
    type: MessageType
    message: str
    additionalText: Optional[str]
    description: Optional[str]

    class Config:
        extra = Extra.forbid


class PConfirmation(BaseModel):
    action: str
    resource: str
    message: PMessage

    class Config:
        extra = Extra.forbid

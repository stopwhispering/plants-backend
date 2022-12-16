from typing import Optional

from pydantic import Extra
from pydantic.main import BaseModel


class PMessage(BaseModel):
    message: str
    additionalText: Optional[str]
    description: Optional[str]
    type: Optional[str]

    class Config:
        extra = Extra.forbid


class PConfirmation(BaseModel):
    action: str
    resource: str
    message: PMessage

    class Config:
        extra = Extra.forbid

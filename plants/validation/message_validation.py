from typing import Optional

from pydantic.main import BaseModel


class PMessage(BaseModel):
    message: str
    additionalText: Optional[str]
    description: Optional[str]
    type: Optional[str]

    class Config:
        extra = 'forbid'


class PConfirmation(BaseModel):
    action: str
    resource: str
    message: PMessage

    class Config:
        extra = 'forbid'

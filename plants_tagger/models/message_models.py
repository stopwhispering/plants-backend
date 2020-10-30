from typing import Optional

from flask_2_ui5_py import MessageType
from pydantic.main import BaseModel


class PMessage(BaseModel):
    type: MessageType
    message: str
    additionalText: Optional[str]
    description: Optional[str]

    class Config:
        extra = 'forbid'

from typing import Optional

from pydantic.main import BaseModel


class PPlantId(BaseModel):
    __root__: int


class PPlantIdOptional(BaseModel):
    __root__: Optional[int]

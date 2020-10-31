from typing import Optional

from pydantic.main import BaseModel


class PTraitCategory(BaseModel):
    id: int
    category_name: str
    sort_flag: Optional[int]   # remove?


class PTrait(BaseModel):
    id: int
    trait: str
    trait_category_id: int
    trait_category: str

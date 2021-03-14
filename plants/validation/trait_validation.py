from typing import Optional, List

from pydantic.main import BaseModel


class PTraitCategory(BaseModel):
    id: int
    category_name: str
    sort_flag: Optional[int]   # remove?

    class Config:
        extra = 'forbid'


class PTrait(BaseModel):
    id: int
    trait: str
    trait_category_id: int
    trait_category: str

    class Config:
        extra = 'forbid'


class PTraitWithStatus(BaseModel):
    id: Optional[int]  # empty if new
    trait: str
    status: str

    class Config:
        extra = 'forbid'


class PTraitCategoryWithTraits(BaseModel):
    """todo: remove after converting to properties model"""
    id: Optional[int]  # empty if new
    category_name: str
    sort_flag: Optional[int]
    traits: List[PTraitWithStatus]

    class Config:
        extra = 'forbid'

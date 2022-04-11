from pathlib import Path
from typing import List, Optional
from datetime import datetime

from pydantic import Field
from pydantic.main import BaseModel

from plants.validation.message_validation import PMessage


class PKeyword(BaseModel):
    keyword: str

    class Config:
        extra = 'forbid'


class PPlantTag(BaseModel):
    plant_id: int = None
    key: str
    text: str

    class Config:
        extra = 'forbid'


class PImage(BaseModel):
    # path_thumb: Path  # not a FilePath as full url is concatenated in frontend
    relative_path_thumb: Path = Field(alias='path_thumb')
    # path_original: Path  # not a FilePath as full url is concatenated in frontend
    relative_path: Path = Field(alias='path_original')
    keywords: List[PKeyword]
    plants: List[PPlantTag]
    description: str
    filename: Path
    # path_full_local: Path  # not a FilePath as existence check would cause performance problems
    absolute_path: Path = Field(alias='path_full_local')
    record_date_time: Optional[datetime]  # 2019-11-21T11:51:13

    class Config:
        extra = 'forbid'
        allow_population_by_field_name = True


class PImageUpdated(BaseModel):
    ImagesCollection: List[PImage]

    class Config:
        extra = 'forbid'


class PResultsImageResource(BaseModel):
    ImagesCollection: List[PImage]
    message: PMessage

    class Config:
        extra = 'forbid'


class PResultsImagesUploaded(BaseModel):
    action: str
    resource: str
    message: PMessage
    images: List[PImage]

    class Config:
        extra = 'forbid'


class PImageUploadedMetadata(BaseModel):
    plants: List[int]
    keywords: List[str]

    class Config:
        extra = 'forbid'


class PResultsImageDeleted(BaseModel):
    action: str
    resource: str
    message: PMessage
    # photo:  PImage

    class Config:
        extra = 'forbid'

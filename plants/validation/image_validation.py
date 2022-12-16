from typing import List, Optional
from datetime import datetime

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
    filename: str
    # relative_path: Path = Field(alias='path_original')  #  todo remove
    keywords: List[PKeyword]
    plants: List[PPlantTag]
    description: str | None
    # absolute_path: Path = Field(alias='path_full_local')#  todo remove
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
    plants: list[int]
    keywords: list[str]

    class Config:
        extra = 'forbid'


class PResultsImageDeleted(BaseModel):
    action: str
    resource: str
    message: PMessage
    # photo_file:  PImage

    class Config:
        extra = 'forbid'

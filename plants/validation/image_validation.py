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
    path_thumb: str  # not a FilePath as full url is concatenated in frontend
    path_original: str  # not a FilePath as full url is concatenated in frontend
    keywords: List[PKeyword]
    plants: List[PPlantTag]
    description: str
    filename: str
    path_full_local: str  # not a FilePath as existence check would cause performance problems
    record_date_time: Optional[datetime]  # 2019-11-21T11:51:13  # todo really optional? seems initial after upload

    class Config:
        extra = 'forbid'


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
    plants: List[str]
    keywords: List[str]

    class Config:
        extra = 'forbid'


class PResultsImageDeleted(BaseModel):
    action: str
    resource: str
    message: PMessage
    photo:  PImage

    class Config:
        extra = 'forbid'
from typing import List, Optional
from datetime import datetime

from pydantic import Extra
from pydantic.main import BaseModel

from plants.validation.message_validation import PMessage


class PKeyword(BaseModel):
    keyword: str

    class Config:
        extra = Extra.forbid


class PImagePlantTag(BaseModel):
    plant_id: int = None
    key: str
    text: str

    class Config:
        extra = Extra.forbid


class PImage(BaseModel):
    filename: str
    keywords: List[PKeyword]
    plants: List[PImagePlantTag]
    description: str | None
    record_date_time: Optional[datetime]  # 2019-11-21T11:51:13

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True


class PImageUpdated(BaseModel):
    ImagesCollection: List[PImage]

    class Config:
        extra = Extra.forbid


class PResultsImageResource(BaseModel):
    ImagesCollection: List[PImage]
    message: PMessage

    class Config:
        extra = Extra.forbid


class PResultsImagesUploaded(BaseModel):
    action: str
    resource: str
    message: PMessage
    images: List[PImage]

    class Config:
        extra = Extra.forbid


class PImageUploadedMetadata(BaseModel):
    plants: list[int]
    keywords: list[str]

    class Config:
        extra = Extra.forbid


class PResultsImageDeleted(BaseModel):
    action: str
    resource: str
    message: PMessage
    # photo_file:  PImage

    class Config:
        extra = Extra.forbid


class GenerateMissingThumbnails(BaseModel):
    count_already_existed: int
    count_generated: int

    class Config:
        extra = Extra.forbid

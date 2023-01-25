from typing import List, Optional
from datetime import datetime

from pydantic import Extra, constr
from pydantic.main import BaseModel

from plants import settings
from plants.schemas.shared import BMessage


####################################################################################################
# Entities used in both API Requests from Frontend and Responses from Backend (FB...)
####################################################################################################
class FBImagePlantTag(BaseModel):
    plant_id: int
    plant_name: constr(min_length=1, max_length=100)
    plant_name_short: constr(min_length=1,
                             max_length=settings.frontend.restrictions.length_shortened_plant_name_for_tag)

    class Config:
        extra = Extra.forbid


class FBKeyword(BaseModel):
    keyword: constr(min_length=1, max_length=100, strip_whitespace=True)

    class Config:
        extra = Extra.forbid


class FBImage(BaseModel):
    id: int
    filename: constr(min_length=1, max_length=150)
    keywords: List[FBKeyword]
    plants: List[FBImagePlantTag]
    description: constr(max_length=500, strip_whitespace=True) | None
    record_date_time: Optional[datetime]  # 2019-11-21T11:51:13

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True


class FBImages(BaseModel):
    __root__: List[FBImage]


####################################################################################################
# Entities used only in API Responses from Backend (B...)
####################################################################################################
class BImageUpdated(BaseModel):
    ImagesCollection: FBImages

    class Config:
        extra = Extra.forbid


class BResultsImageResource(BaseModel):
    ImagesCollection: FBImages
    message: BMessage

    class Config:
        extra = Extra.forbid


class BResultsImagesUploaded(BaseModel):
    action: str
    message: BMessage
    images: FBImages

    class Config:
        extra = Extra.forbid


class BResultsImageDeleted(BaseModel):
    action: str
    message: BMessage
    # photo_file:  PImage

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API Requests from Frontend (F...)
####################################################################################################
class FImageUploadedMetadata(BaseModel):
    plants: list[int]
    keywords: list[constr(min_length=1, max_length=100, strip_whitespace=True)]

    class Config:
        extra = Extra.forbid

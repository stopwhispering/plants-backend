from datetime import datetime
from typing import List, Optional

from pydantic import constr

from plants import settings
from plants.shared.base_schema import (BaseSchema, RequestContainer,
                                       ResponseContainer)
from plants.shared.message_schemas import BMessage


class FBImagePlantTag(BaseSchema):
    plant_id: int
    plant_name: constr(min_length=1, max_length=100)
    plant_name_short: constr(min_length=1,
                             max_length=settings.frontend.restrictions.length_shortened_plant_name_for_tag)


class FBKeyword(BaseSchema):
    keyword: constr(min_length=1, max_length=100)


class ImageBase(BaseSchema):
    id: int
    filename: constr(min_length=1, max_length=150)
    keywords: List[FBKeyword]
    plants: List[FBImagePlantTag]
    description: constr(max_length=500) | None
    record_date_time: Optional[datetime]  # 2019-11-21T11:51:13


class ImageCreateUpdate(ImageBase):
    pass


class ImageRead(ImageBase):
    pass


class BImageUpdated(RequestContainer):
    ImagesCollection: list[ImageCreateUpdate]


class BResultsImageResource(ResponseContainer):
    ImagesCollection: list[ImageRead]


class BResultsImagesUploaded(ResponseContainer):
    images: list[ImageRead]


class BResultsImageDeleted(ResponseContainer):
    action: str
    message: BMessage


class FImageUploadedMetadata(BaseSchema):
    plants: list[int]
    keywords: list[constr(min_length=1, max_length=100)]

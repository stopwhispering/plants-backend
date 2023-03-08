from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import constr, validator

from plants import settings
from plants.modules.image.models import ImageKeyword
from plants.modules.image.util import shorten_plant_name
from plants.modules.plant.models import Plant
from plants.shared.base_schema import BaseSchema, RequestContainer, ResponseContainer
from plants.shared.message_schemas import BMessage


class FBImagePlantTag(BaseSchema):
    plant_id: int
    plant_name: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    plant_name_short: constr(  # type: ignore[valid-type]
        min_length=1,
        max_length=settings.frontend.restrictions.length_shortened_plant_name_for_tag,
    )


class FBKeyword(BaseSchema):
    keyword: constr(min_length=1, max_length=100)  # type: ignore[valid-type]


class ImageBase(BaseSchema):
    id: int
    filename: constr(min_length=1, max_length=150)  # type: ignore[valid-type]
    keywords: list[FBKeyword]
    plants: list[FBImagePlantTag]
    description: constr(max_length=500) | None  # type: ignore[valid-type]
    record_date_time: Optional[datetime]  # 2019-11-21T11:51:13


class ImageCreateUpdate(ImageBase):
    pass


class ImageRead(ImageBase):
    # noinspection PyMethodParameters
    @validator("keywords", pre=True)
    def _transform_keywords(
        cls, keywords: list[ImageKeyword]
    ) -> list[dict[str, object]]:
        return [{"keyword": k.keyword} for k in keywords]

    # noinspection PyMethodParameters
    @validator("plants", pre=True)
    def _transform_plants(cls, plants: list[Plant]) -> list[dict[str, object]]:
        return [
            {
                "plant_id": p.id,
                "plant_name": p.plant_name,
                "plant_name_short": (
                    shorten_plant_name(
                        p.plant_name,
                        settings.frontend.restrictions.length_shortened_plant_name_for_tag,
                    )
                ),
                "key": p.plant_name,
            }
            for p in plants
        ]


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
    keywords: list[constr(min_length=1, max_length=100)]  # type: ignore[valid-type]

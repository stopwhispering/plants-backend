from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from plants import settings
from plants.modules.image.models import ImageKeyword
from plants.modules.image.util import shorten_plant_name
from plants.modules.plant.models import Plant
from plants.shared.base_schema import BaseSchema, RequestContainer, ResponseContainer


class ImagePlantTag(BaseSchema):
    plant_id: int
    plant_name: Annotated[str, Field(min_length=1, max_length=1_000)]
    plant_name_short: Annotated[
        str,
        Field(
            min_length=1,
            max_length=settings.frontend.restrictions.length_shortened_plant_name_for_tag,
        ),
    ]


class Keyword(BaseSchema):
    keyword: Annotated[str, Field(min_length=1, max_length=100)]


class ImageBase(BaseSchema):
    id: int
    filename: Annotated[str, Field(min_length=1, max_length=150)]
    keywords: list[Keyword]
    plants: list[ImagePlantTag]
    description: Annotated[str, Field(max_length=500)] | None = None
    record_date_time: datetime | None = None  # 2019-11-21T11:51:13


class ImageCreateUpdate(ImageBase):
    pass


class ImageRead(ImageBase):
    # noinspection PyMethodParameters
    @field_validator("keywords", mode="before")  # noqa
    @classmethod
    def _transform_keywords(cls, keywords: list[ImageKeyword]) -> list[dict[str, object]]:
        return [{"keyword": k.keyword} for k in keywords]

    # noinspection PyMethodParameters
    @field_validator("plants", mode="before")  # noqa
    @classmethod
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


class UpdateImageRequest(RequestContainer):
    ImagesCollection: list[ImageCreateUpdate]


class GetUntaggedImagesResponse(ResponseContainer):
    ImagesCollection: list[ImageRead]


class UploadImagesResponse(ResponseContainer):
    images: list[ImageRead]


class LastImageUploadTimestampResponse(ResponseContainer):
    timestamp: datetime | None


class DeleteImagesResponse(ResponseContainer):
    pass


class UploadedImageMetadata(BaseSchema):
    plants: list[int]
    keywords: list[Annotated[str, Field(min_length=1, max_length=100)]]

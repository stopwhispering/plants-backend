import datetime
from typing import NamedTuple, TypedDict, List, Optional


class ImageInfo(NamedTuple):
    date: datetime.date
    path: str
    path_thumb: str


# class PlantImageTagExt(TypedDict):
#     # tododelme
#     key: str
#     text: str
#     plant_id: Optional[int]


# class KeywordImageTagExt(TypedDict):
#     # todo delme
#     keyword: str


# class PhotoFileExt(TypedDict):
#     """
#     TODO DELME
#     metadata on photo files from Exif Tags; used to submit to frontend
#     """
#     path_thumb: str
#     path_original: str
#     keywords: List[KeywordImageTagExt]
#     plants: List[PlantImageTagExt]
#     description: str
#     filename: str
#     path_full_local: str
#     record_date_time: datetime.datetime

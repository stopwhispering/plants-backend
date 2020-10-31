import datetime
from typing import NamedTuple


class ImageInfo(NamedTuple):
    date: datetime.date
    path: str
    path_thumb: str

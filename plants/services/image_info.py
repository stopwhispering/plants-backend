import datetime
from pathlib import PurePath
from typing import NamedTuple


class ImageInfo(NamedTuple):
    date: datetime.date
    path: PurePath
    path_thumb: PurePath
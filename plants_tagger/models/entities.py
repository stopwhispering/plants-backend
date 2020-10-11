import datetime
from typing import NamedTuple


# class ImageInfo:
#     def __init__(self, date=None, path=None):
#         self.date: datetime.date = date
#         self.path: str = path


class ImageInfo(NamedTuple):
    date: datetime.date
    path: str
    path_thumb: str

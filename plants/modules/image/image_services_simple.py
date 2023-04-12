from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PIL import Image

from plants import settings

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def original_image_file_exists(filename: str) -> bool:
    return settings.paths.path_original_photos_uploaded.joinpath(filename).is_file()


def remove_image_from_filesystem(filename: str) -> None:
    settings.paths.path_original_photos_uploaded.joinpath(filename).unlink()


def resizing_required(path: str | Path, size: tuple[int, int]) -> bool:
    """Checks size of photo_file at supplied path and compares to supplied maximum size."""
    with Image.open(path) as image:  # only works with path, not file object
        x, y = image.size
    if x > size[0]:
        y = int(max(y * size[0] / x, 1))
        x = int(size[0])
    if y > size[1]:
        x = int(max(x * size[1] / y, 1))
        y = int(size[1])
    size = x, y
    return bool(size != image.size)

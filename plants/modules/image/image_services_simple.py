from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PilImage

from plants import settings

logger = logging.getLogger(__name__)


def original_image_file_exists(filename: str) -> bool:
    return settings.paths.path_original_photos_uploaded.joinpath(filename).is_file()


def remove_image_from_filesystem(filename: str) -> None:
    settings.paths.path_original_photos_uploaded.joinpath(filename).unlink()


async def is_resizing_required(pil_image: PilImage, size: tuple[int, int] | None) -> bool:
    """Checks size of PIL Image and compares to supplied maximum size."""
    if not size:
        return False

    x, y = pil_image.size
    if x > size[0]:
        y = int(max(y * size[0] / x, 1))
        x = int(size[0])
    if y > size[1]:
        x = int(max(x * size[1] / y, 1))
        y = int(size[1])
    size = x, y
    return bool(size != pil_image.size)

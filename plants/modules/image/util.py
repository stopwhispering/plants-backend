from __future__ import annotations

import datetime
import logging
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any, Optional, Union

import piexif
import pytz
from PIL import Image as PilImage

from plants.shared.api_constants import FORMAT_FILENAME_TIMESTAMP

if TYPE_CHECKING:
    from io import BytesIO

logger = logging.getLogger(__name__)

_ORIENT_180 = 3
_ORIENT_270 = 6
_ORIENT_90 = 8


def get_thumbnail_name(filename: str, size: tuple[int, int]) -> str:
    suffix = f"{size[0]}_{size[1]}"
    filename_thumb_list = filename.split(".")
    # noinspection PyTypeChecker
    filename_thumb_list.insert(-1, suffix)
    return ".".join(filename_thumb_list)


def generate_thumbnail(
    image: Union[Path, BytesIO],
    path_thumbnail: Path,
    size: tuple[int, int] = (100, 100),
    filename_thumb: Union[PurePath, str] | None = None,
    *,
    ignore_missing_image_files: bool = False,
) -> Optional[Path]:
    """Generates a resized variant of an photo_file; returns the full local path supply
    original photo_file either as filename or i/o stream if Image is supplied as
    BytesIO, a filename_thumb <<must>> be supplied."""
    if not ignore_missing_image_files:
        logger.debug(f"Generating resized photo_file of {image} in size {size}.")
    # suffix = f'{size[0]}_{size[1]}'

    if isinstance(image, Path) and not image.is_file():
        if not ignore_missing_image_files:
            logger.error(
                f"Original Image of default photo_file does not exist. Can't generate "
                f"thumbnail. {image}"
            )
        return None
    im = PilImage.open(image)

    # there's a bug in chrome: it's not respecting the orientation exif (unless directly
    # opened in chrome)
    # therefore hard-rotate thumbnail according to that exif tag
    # noinspection PyProtectedMember
    exif_obj: dict[str, Any] = im._getexif()  # type: ignore[attr-defined]  # noqa: SLF001
    if exif_obj:
        im = _rotate_if_required(im, exif_obj)

    im.thumbnail(size)

    if not filename_thumb:
        filename_thumb = get_thumbnail_name(image.name, size)

    path_save = path_thumbnail.joinpath(filename_thumb)
    im.save(path_save, "JPEG")

    return path_save


def _rotate_if_required(
    image: PilImage.Image, exif_obj: dict[str, Any]
) -> PilImage.Image:
    """Rotate photo_file if exif file has a rotate directive (solves chrome bug not
    respecting orientation exif tag) no exif tag manipulation required as this is not
    saved to thumbnails anyway."""
    # noinspection PyProtectedMember
    exif = dict(exif_obj.items())
    if piexif.ImageIFD.Orientation in exif:
        if exif[piexif.ImageIFD.Orientation] == _ORIENT_180:
            return image.rotate(180, expand=True)
        if exif[piexif.ImageIFD.Orientation] == _ORIENT_270:
            return image.rotate(270, expand=True)
        if exif[piexif.ImageIFD.Orientation] == _ORIENT_90:
            return image.rotate(90, expand=True)
    return image


def resize_image(
    path: Path, save_to_path: Path, size: tuple[int, int], quality: int
) -> None:
    """load photo_file at supplied path, save resized photo_file to other path; observes
    size and quality params; original file is finally <<deleted>>"""
    with PilImage.open(path.as_posix()) as image:
        image.thumbnail(size)  # preserves aspect ratio
        if image.info.get("exif"):
            image.save(
                save_to_path.as_posix(),
                quality=quality,
                exif=image.info.get("exif"),
                optimize=True,
            )
        else:  # fix some bug with ebay images that apparently have no exif part
            logger.info("Saving w/o exif.")
            image.save(save_to_path.as_posix(), quality=quality, optimize=True)

    if path != save_to_path:
        path.unlink()  # delete file


def generate_timestamp_filename() -> str:
    dt_cet = datetime.datetime.now(tz=pytz.timezone("Europe/Berlin"))
    return f"{dt_cet.strftime(FORMAT_FILENAME_TIMESTAMP)}.jpg"

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import piexif
import pytz
from PIL import Image as PilImage

from plants.shared.api_constants import FORMAT_FILENAME_TIMESTAMP

if TYPE_CHECKING:
    from io import BytesIO

    from PIL.Image import Exif

    from plants.modules.image.save import UploadImage

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


def generate_thumbnail_for_pil_image(
    pil_image: PilImage.Image,
    thumbnail_folder: Path,
    thumbnail_filename: str,
    size: tuple[int, int] = (100, 100),
    *,
    ignore_missing_image_files: bool = False,
) -> Path | None:
    """Generate a resized variant of a PIL Image; returns the full local path."""
    if not ignore_missing_image_files:
        logger.debug(f"Generating resized photo_file in size {size}.")

    # PIL's thumbnail() fn works inplace, so we clone the image, first
    thumbnail = pil_image.copy()

    # there's a bug in chrome: it's not respecting the orientation exif (unless directly
    # opened in chrome)
    # therefore hard-rotate thumbnail according to that exif tag
    # noinspection PyProtectedMember
    exif_obj: Exif = pil_image.getexif()  # _getexif()
    # exif_obj: dict[str, Any] = pil_image._getexif()
    if exif_obj:
        thumbnail = _rotate_if_required(thumbnail, exif_obj)

    thumbnail.thumbnail(size)

    path_save = thumbnail_folder.joinpath(thumbnail_filename)
    thumbnail.save(path_save, "JPEG")

    return path_save


def generate_thumbnail(
    image: Path | BytesIO,
    thumbnail_folder: Path,
    thumbnail_filename: str,
    size: tuple[int, int] = (100, 100),
    *,
    ignore_missing_image_files: bool = False,
) -> Path | None:
    """Generates a resized variant of an photo_file; returns the full local path supply original
    photo_file either as filename or i/o stream if Image is supplied as BytesIO, a filename_thumb.

    <<must>> be supplied.
    """

    if isinstance(image, Path) and not image.is_file():
        if not ignore_missing_image_files:
            logger.error(
                f"Original Image of default photo_file does not exist. Can't generate "
                f"thumbnail. {image}"
            )
        return None
    # works with both Path to JPEG flie and BytesIO object
    pil_image = PilImage.open(image)

    return generate_thumbnail_for_pil_image(
        pil_image=pil_image,
        thumbnail_folder=thumbnail_folder,
        size=size,
        thumbnail_filename=thumbnail_filename,
        ignore_missing_image_files=ignore_missing_image_files,
    )


def _rotate_if_required(image: PilImage.Image, exif_obj: Exif) -> PilImage.Image:
    """Rotate photo_file if exif file has a rotate directive (solves chrome bug not respecting
    orientation exif tag) no exif tag manipulation required as this is not saved to thumbnails
    anyway."""
    # noinspection PyTypeChecker
    exif = dict(exif_obj.items())
    if piexif.ImageIFD.Orientation in exif:
        if exif[piexif.ImageIFD.Orientation] == _ORIENT_180:
            return image.rotate(180, expand=True)
        if exif[piexif.ImageIFD.Orientation] == _ORIENT_270:
            return image.rotate(270, expand=True)
        if exif[piexif.ImageIFD.Orientation] == _ORIENT_90:
            return image.rotate(90, expand=True)
    return image


async def resize_and_save(upload_image: UploadImage, size: tuple[int, int], quality: int) -> None:
    """Resize and save supplied PIL Image to path; observes size and quality params."""

    # file_content: bytes = await file.read()
    # image_file: ImageFile = PilImage.open(io.BytesIO(file_content))
    # PIL's thumnail fn works inplace, so we need to clone
    thumbnail = upload_image.pil_image.copy()
    thumbnail.thumbnail(size)  # preserves aspect ratio
    if thumbnail.info.get("exif"):
        thumbnail.save(
            upload_image.path.as_posix(),
            quality=quality,
            exif=thumbnail.info.get("exif"),
            optimize=True,
        )
    else:  # fix some bug with ebay images that apparently have no exif part
        logger.info("Saving w/o exif.")
        thumbnail.save(upload_image.path.as_posix(), quality=quality, optimize=True)

    # if path != save_to_path:
    #     path.unlink()  # delete file


def generate_timestamp_filename() -> str:
    dt_cet = datetime.datetime.now(tz=pytz.timezone("Europe/Berlin"))
    return f"{dt_cet.strftime(FORMAT_FILENAME_TIMESTAMP)}.jpg"


def shorten_plant_name(plant_name: str, max_length: int) -> str:
    """Shorten plant name to 20 chars for display in ui5 table."""
    return plant_name[: max_length - 3] + "..." if len(plant_name) > max_length else plant_name

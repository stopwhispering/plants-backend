from pathlib import Path, PurePath
from typing import Union, Optional, Sequence
import piexif
from PIL import Image
import logging
from io import BytesIO
from PIL.JpegImagePlugin import JpegImageFile

from plants import config

logger = logging.getLogger(__name__)


def generate_thumbnail(image: Union[Path, BytesIO],
                       path_thumbnail: Path,
                       size: Sequence = (100, 100),
                       filename_thumb: Union[PurePath, str] = None) -> Optional[Path]:
    """
    generates a resized variant of an photo; returns the full local path
    supply original photo either as filename or i/o stream
    if Image is supplied as BytesIO, a filename_thumb <<must>> be supplied
    """
    if not config.log_ignore_missing_image_files:
        logger.debug(f'Generating resized photo of {image} in size {size}.')
    suffix = f'{size[0]}_{size[1]}'

    if isinstance(image, Path) and not image.is_file():
        if not config.log_ignore_missing_image_files:
            logger.error(f"Original Image of default photo does not exist. Can't generate thumbnail. {image}")
        return
    im = Image.open(image)

    # there's a bug in chrome: it's not respecting the orientation exif (unless directly opened in chrome)
    # therefore hard-rotate thumbnail according to that exif tag
    # noinspection PyProtectedMember
    exif_obj = im._getexif()  # noqa
    im = _rotate_if_required(im, exif_obj)  # noqa

    im.thumbnail(tuple(size))

    if not filename_thumb:
        filename_thumb_list = image.name.split('.')
        # noinspection PyTypeChecker
        filename_thumb_list.insert(-1, suffix)
        filename_thumb = ".".join(filename_thumb_list)

    path_save = path_thumbnail.joinpath(filename_thumb)
    im.save(path_save, "JPEG")

    return path_save


def _rotate_if_required(image: JpegImageFile, exif_obj: Optional[dict]):
    """
    rotate photo if exif file has a rotate directive
    (solves chrome bug not respecting orientation exif tag)
    no exif tag manipulation required as this is not saved
    to thumbnails anyway
    """
    if exif_obj:  # the photo might have no exif-tags
        # noinspection PyProtectedMember
        exif = dict(exif_obj.items())
        if piexif.ImageIFD.Orientation in exif:
            if exif[piexif.ImageIFD.Orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[piexif.ImageIFD.Orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[piexif.ImageIFD.Orientation] == 8:
                image = image.rotate(90, expand=True)
    return image

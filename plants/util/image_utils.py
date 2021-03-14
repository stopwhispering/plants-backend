import os
from typing import Union, Optional
import piexif
from PIL import Image
import logging
from io import BytesIO
from PIL.JpegImagePlugin import JpegImageFile

from plants.config_local import LOG_IS_DEV

logger = logging.getLogger(__name__)


def generate_thumbnail(image: Union[str, BytesIO],
                       size: tuple = (100, 100),
                       path_thumbnail: str = '',
                       filename_thumb: str = '') -> Optional[str]:
    """
    generates a resized variant of an image; returns the full local path
    supply original image either as filename or i/o stream
    if Image is supplied as BytesIO, a filename <<must>> be supplied
    """
    if not LOG_IS_DEV:
        logger.debug(f'Generating resized image of {image} in size {size}.')
    suffix = f'{size[0]}_{size[1]}'

    if type(image) == str and not os.path.isfile(image):
        if not LOG_IS_DEV:
            logger.error(f"Original Image of default image does not exist. Can't generate thumbnail. {image}")
        return
    im = Image.open(image)

    # there's a bug in chrome: it's not respecting the orientation exif (unless directly opened in chrome)
    # therefore hard-rotate thumbnail according to that exif tag
    # noinspection PyProtectedMember
    exif_obj = im._getexif()
    im = _rotate_if_required(im, exif_obj)

    im.thumbnail(size)

    if not filename_thumb:
        filename_image = os.path.basename(image)
        filename_thumb_list = filename_image.split('.')
        # noinspection PyTypeChecker
        filename_thumb_list.insert(-1, suffix)
        filename_thumb = ".".join(filename_thumb_list)

    path_save = os.path.join(path_thumbnail, filename_thumb)
    im.save(path_save, "JPEG")

    return path_save


def _rotate_if_required(image: JpegImageFile, exif_obj: Optional[dict]):
    """
    rotate image if exif file has a rotate directive
    (solves chrome bug not respecting orientation exif tag)
    no exif tag manipulation required as this is not saved
    to thumbnails anyway
    """
    if exif_obj:  # the image might have no exif-tags
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

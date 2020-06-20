import os
import piexif
from PIL import Image
import logging

from plants_tagger.config_local import LOG_IS_DEV

logger = logging.getLogger(__name__)


def generate_thumbnail(path_image: str,
                       size: tuple = (100, 100),
                       path_thumbnail: str = ''):
    """ generates a resized variant of an image; returns the full local path"""
    if not LOG_IS_DEV:
        logger.debug(f'generating resized image of {path_image} in size {size}.')
    suffix = f'{size[0]}_{size[1]}'
    if not os.path.isfile(path_image):
        if not LOG_IS_DEV:
            logger.error(f"Original Image of default image does not exist. Can't generate thumbnail. {path_image}")
        return
    im = Image.open(path_image)

    # there's a bug in chrome: it's not respecting the orientation exif (unless directly opened in chrome)
    # therefore hard-rotate thumbnail according to that exif tag
    # noinspection PyProtectedMember
    exif_obj = im._getexif()
    _rotate_if_required(im, exif_obj)

    im.thumbnail(size)
    filename_image = os.path.basename(path_image)
    filename_thumb_list = filename_image.split('.')
    # noinspection PyTypeChecker
    filename_thumb_list.insert(-1, suffix)
    filename_thumb = ".".join(filename_thumb_list)
    path_save = os.path.join(path_thumbnail, filename_thumb)
    im.save(path_save, "JPEG")

    # thumbnails don't require any exif tags
    # exif_dict = piexif.load(path)
    # exif_bytes = piexif.dump(exif_dict)
    # piexif.insert(exif_bytes, path_new)

    return path_save


def _rotate_if_required(image, exif_obj):
    """rotate image if exif file has a rotate directive"""
    if exif_obj:  # the image might have no exif-tags
        # noinspection PyProtectedMember
        exif = dict(image._getexif().items())
        if piexif.ImageIFD.Orientation in exif:
            if exif[piexif.ImageIFD.Orientation] == 3:
                _ = image.rotate(180, expand=True)
            elif exif[piexif.ImageIFD.Orientation] == 6:
                _ = image.rotate(270, expand=True)
            elif exif[piexif.ImageIFD.Orientation] == 8:
                _ = image.rotate(90, expand=True)
    return image

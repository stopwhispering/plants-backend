from pathlib import PurePath, Path
from typing import List, Tuple
import logging

from PIL import Image

from plants import config
from plants.util.filename_utils import get_generated_filename, with_suffix
from plants.util.image_utils import generate_thumbnail

logger = logging.getLogger(__name__)


def get_filename_thumb(filename: str) -> str:
    return get_generated_filename(filename,
                                  size=config.size_thumbnail_image)


def get_relative_path_thumb(filename_thumb: str) -> PurePath:  # todo remove
    return config.rel_path_photos_generated.joinpath(filename_thumb)


def remove_files_already_existing(files: List, suffix: str) -> List[str]:
    """
    iterates over file objects, checks whether a file with that name already exists in filesystem; removes already
    existing files from files list and returns a list of already existing file names
    """
    duplicate_filenames = []
    for photo_upload in files[:]:  # need to loop on copy if we want to delete within loop
        path = config.path_original_photos_uploaded.joinpath(photo_upload.filename)
        logger.debug(f'Checking uploaded photo_file ({photo_upload.content_type}) to be saved as {path}.')
        if path.is_file() or with_suffix(path, suffix).is_file():
            files.remove(photo_upload)
            duplicate_filenames.append(photo_upload.filename)
            logger.warning(f'Skipping file upload (duplicate) for: {photo_upload.filename}')
    return duplicate_filenames


def resizing_required(path: str, size: Tuple[int, int]) -> bool:
    """
    checks size of photo_file at supplied path and compares to supplied maximum size
    """
    with Image.open(path) as image:  # only works with path, not file object
        x, y = image.size
    if x > size[0]:
        y = int(max(y * size[0] / x, 1))
        x = int(size[0])
    if y > size[1]:
        x = int(max(x * size[1] / y, 1))
        y = int(size[1])
    size = x, y
    return size != image.size


def get_path_for_taxon_thumbnail(filename: Path):
    return config.rel_path_photos_generated_taxon.joinpath(filename)


def generate_previewimage_if_not_exists(original_image_rel_path: PurePath):
    """
     generates a preview image for a plant's default if it does not yet exist"""
    filename_generated = get_generated_filename(filename_original=original_image_rel_path.name,
                                                size=config.size_preview_image)
    path_full = config.path_photos_base.parent.joinpath(original_image_rel_path)
    path_generated = config.path_generated_thumbnails.joinpath(filename_generated)

    if not path_generated.is_file():
        # if not config.ignore_missing_image_files:
        #     logger.info('Preview Image: Generating the not-yet-existing preview photo_file.')
        generate_thumbnail(image=path_full,
                           size=config.size_preview_image,
                           path_thumbnail=config.path_generated_thumbnails)


def get_previewimage_rel_path(original_image_rel_path: PurePath) -> Path:
    """
    get plant's default photo_file's relative path
    """
    filename_generated = get_generated_filename(filename_original=original_image_rel_path.name,
                                                size=config.size_preview_image)
    return config.rel_path_photos_generated.joinpath(filename_generated)


def get_relative_path(absolute_path: Path) -> PurePath:
    # todo better with .parent?
    rel_path_photos_original = config.rel_path_photos_original.as_posix()
    absolute_path_str = absolute_path.as_posix()
    return PurePath(absolute_path_str[absolute_path_str.find(rel_path_photos_original):])
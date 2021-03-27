from itertools import chain
from typing import Tuple, List, Generator
import os
from PIL import Image
import logging
from typing import Set

import plants.config_local
import plants.services.PhotoDirectory
import plants.services.os_paths
from plants import config
from plants.config_local import LOG_IS_DEV
from plants.services.PhotoDirectory import lock_photo_directory, get_photo_directory
from plants.services.Photo import Photo
from plants.services.exif_services import rename_plant_in_exif_tags
from plants.services.os_paths import (REL_PATH_PHOTOS_GENERATED, PATH_GENERATED_THUMBNAILS,
                                      REL_PATH_PHOTOS_GENERATED_TAXON, PATH_ORIGINAL_PHOTOS_UPLOADED)
from plants.util.filename_utils import get_generated_filename, with_suffix
from plants.util.image_utils import generate_thumbnail

logger = logging.getLogger(__name__)


def generate_previewimage_get_rel_path(original_image_rel_path_raw: str) -> str:
    """
    generates a preview image for a plant's default image if not exists, yet
    returns the relative path to it
    """
    if os.name == 'nt':  # handle forward- and backslash for linux/windows systems
        original_image_rel_path = original_image_rel_path_raw.replace('/', '\\')
    else:
        original_image_rel_path = original_image_rel_path_raw.replace('\\', '/')

    # get filename of preview image and check if that file already exists
    filename_original = os.path.basename(original_image_rel_path)
    filename_generated = get_generated_filename(filename_original,
                                                size=config.size_preview_image)

    path_full = os.path.join(plants.services.os_paths.PATH_PHOTOS_BASE, original_image_rel_path)
    path_generated = os.path.join(PATH_GENERATED_THUMBNAILS, filename_generated)
    if not os.path.isfile(path_generated):
        if not LOG_IS_DEV:
            logger.info('Preview Image: Generating the not-yet-existing preview image.')
        generate_thumbnail(image=path_full,
                           size=config.size_preview_image,
                           path_thumbnail=os.path.join(plants.config_local.PATH_BASE, REL_PATH_PHOTOS_GENERATED))

    return os.path.join(plants.services.os_paths.REL_PATH_PHOTOS_GENERATED, filename_generated)


def get_thumbnail_relative_path_for_relative_path(path_relative: str, size: tuple) -> str:
    """
    returns relative path of the corresponding thumbnail for an image file's relative path
    """
    filename = os.path.basename(path_relative)
    filename_thumbnail = get_generated_filename(filename, size)
    return os.path.join(REL_PATH_PHOTOS_GENERATED, filename_thumbnail)


def get_path_for_taxon_thumbnail(filename: str):
    return os.path.join(REL_PATH_PHOTOS_GENERATED_TAXON, filename)


def get_distinct_keywords_from_image_files() -> Set[str]:
    """
    get set of all keywords from all the images in the directory
    """
    with lock_photo_directory:
        photo_directory = get_photo_directory()

        # get flattening generator and create set of distinct keywords
        keywords_nested_gen = (photo.tag_keywords for photo in photo_directory.photos if photo.tag_keywords)
        return set(chain.from_iterable(keywords_nested_gen))


def resizing_required(path: str, size: Tuple[int, int]) -> bool:
    """
    checks size of image at supplied path and compares to supplied maximum size
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


def resize_image(path: str, save_to_path: str, size: Tuple[int, int], quality: int) -> None:
    """
    load image at supplied path, save resized image to other path; observes size and quality params;
    original file is finally <<deleted>>
    """
    with Image.open(path) as image:
        image.thumbnail(size)  # preserves aspect ratio
        if image.info.get('exif'):
            image.save(save_to_path,
                       quality=quality,
                       exif=image.info.get('exif'),
                       optimize=True)
        else:  # fix some bug with ebay images that apparently have no exif part
            logger.info("Saving w/o exif.")
            image.save(save_to_path,
                       quality=quality,
                       optimize=True)

    if path != save_to_path:
        os.remove(path)


def _get_images_by_plant_name(plant_name: str) -> Generator[Photo, None, None]:
    """
    returns generator of image entries from photo directory tagging supplied plant name
    """
    with lock_photo_directory:
        photo_directory = get_photo_directory()
        return (p for p in photo_directory.photos if plant_name in p.tag_authors_plants)
    # isinstance(p.tag_authors_plants, list) and plant_name in p.tag_authors_plants]


def rename_plant_in_image_files(plant_name_old: str, plant_name_new: str) -> int:
    """
    in each image file that has the old plant name tagged in exif, switch tag to the new plant name
    """
    # get the relevant images from the photo directory cache
    images = _get_images_by_plant_name(plant_name_old)
    count_modified = 0
    if not images:
        logger.info(f'No image tag to change for {plant_name_old}.')

    for image in images:
        # double check
        if plant_name_old in image.tag_authors_plants:
            logger.info(f"Switching plant tag in image file {image.path_full_local}")
            rename_plant_in_exif_tags(image, plant_name_old, plant_name_new)
            count_modified += 1

    # note: there's no need to upload the cache as we did modify directly in the cache above
    return count_modified


# def remove_files_already_existing(files: List[FileStorage], suffix: str) -> List[str]:  # todo
def remove_files_already_existing(files: List, suffix: str) -> List[str]:
    """
    iterates over file objects, checks whether a file with that name already exists in filesystem; removes already
    existing files from files list and returns a list of already existing file names
    """
    duplicate_filenames = []
    for photo_upload in files[:]:  # need to loop on copy if we want to delete within loop
        path = os.path.join(PATH_ORIGINAL_PHOTOS_UPLOADED, photo_upload.filename)
        # logger.debug(f'Checking uploaded photo ({photo_upload.mimetype}) to be saved as {path}.')
        logger.debug(f'Checking uploaded photo ({photo_upload.content_type}) to be saved as {path}.')
        if os.path.isfile(path) or os.path.isfile(with_suffix(path, suffix)):  # todo: better check all folders!
            files.remove(photo_upload)
            duplicate_filenames.append(photo_upload.filename)
            logger.warning(f'Skipping file upload (duplicate) for: {photo_upload.filename}')
    return duplicate_filenames

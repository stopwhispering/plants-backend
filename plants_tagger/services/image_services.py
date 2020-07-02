from typing import Tuple
import os
from PIL import Image
import functools
import operator
import threading
import logging
from typing import Set

import plants_tagger.config_local
import plants_tagger.services.os_paths
from plants_tagger import config
from plants_tagger.config_local import PATH_BASE, LOG_IS_DEV
from plants_tagger.services.PhotoDirectory import PhotoDirectory
from plants_tagger.services.exif_services import rename_plant_in_exif_tags
from plants_tagger.services.os_paths import REL_PATH_PHOTOS_GENERATED, \
    PATH_GENERATED_THUMBNAILS, PATH_ORIGINAL_PHOTOS
from plants_tagger.util.filename_utils import get_generated_filename
from plants_tagger.util.image_utils import generate_thumbnail

lock_photo_directory = threading.RLock()
photo_directory = None
logger = logging.getLogger(__name__)


def generate_previewimage_get_rel_path(original_image_rel_path_raw):
    """generates a preview image for a plant's default image if not exists, yet; returns the relative path to it"""
    # get filename of preview image and check if that file already exists

    if os.name == 'nt':  # handle forward- and backslash for linux/windows systems
        original_image_rel_path = original_image_rel_path_raw.replace('/', '\\')
    else:
        original_image_rel_path = original_image_rel_path_raw.replace('\\', '/')

    filename_original = os.path.basename(original_image_rel_path)
    filename_generated = get_generated_filename(filename_original,
                                                size=config.size_preview_image)

    path_full = os.path.join(plants_tagger.services.os_paths.PATH_PHOTOS_BASE, original_image_rel_path)
    path_generated = os.path.join(PATH_GENERATED_THUMBNAILS, filename_generated)
    if not os.path.isfile(path_generated):
        if not LOG_IS_DEV:
            logger.info('Preview Image: Generating the not-yet-existing preview image.')
        generate_thumbnail(path_image=path_full,
                           size=config.size_preview_image,
                           path_thumbnail=os.path.join(plants_tagger.config_local.PATH_BASE, REL_PATH_PHOTOS_GENERATED))

    rel_path = os.path.join(plants_tagger.services.os_paths.REL_PATH_PHOTOS_GENERATED, filename_generated)
    return rel_path


def get_thumbnail_relative_path_for_relative_path(path_relative: str, size: tuple):
    filename = os.path.basename(path_relative)
    filename_thumbnail = get_generated_filename(filename, size)
    path_relative_thumbnail = os.path.join(REL_PATH_PHOTOS_GENERATED, filename_thumbnail)
    return path_relative_thumbnail


def get_plants_data(directory):
    """extracts information from the directory that is relevant for the frontend;
    returns list of dicts (just like directory)"""
    plants_data = [
        {"url_small": file.get('path_thumb') or '',
         "url_original": file.get('path_original') or '',
         "keywords": file['tag_keywords'],
         "plants": file['tag_authors_plants'],
         "description": file.get('tag_description') or '',
         "filename": file['filename'] if 'filename' in file else '',
         "path_full_local": file['path_full_local'],
         "record_date_time": file['record_date_time']
         } for file in directory]
    return plants_data


def get_exif_tags_for_folder():
    """get list of image dicts; uses global photo directory object, initialized only
    at first time after server (re-)start"""
    with lock_photo_directory:
        global photo_directory
        if not photo_directory:
            photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
            photo_directory.refresh_directory(PATH_BASE)
        plants_data = get_plants_data(photo_directory.directory)
        plants_unique = photo_directory.get_all_plants()
    return plants_data, plants_unique


def get_distinct_keywords_from_image_files() -> Set[str]:
    """get set of all keywords from all the images in the directory"""
    with lock_photo_directory:
        global photo_directory
        if not photo_directory:
            photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
            photo_directory.refresh_directory(PATH_BASE)

        # get list of lists of strings, flatten that nested list and return the distinct keywords as set
        keywords_nested_list = [file.get('tag_keywords') for file in photo_directory.directory]
        keywords_nested_list = [li for li in keywords_nested_list if li]  # remove None's
        keywords_list = functools.reduce(operator.concat, keywords_nested_list)
        return set(keywords_list)


def resizing_required(path, size):
    with Image.open(path) as image:  # only works with path, not file object
        # image = Image.open(file_obj)
        x, y = image.size
    if x > size[0]:
        y = int(max(y * size[0] / x, 1))
        x = int(size[0])
    if y > size[1]:
        x = int(max(x * size[1] / y, 1))
        y = int(size[1])
    size = x, y
    return size != image.size


def resize_image(path: str, save_to_path: str, size: Tuple[int, int], quality: int):
    with Image.open(path) as image:
        # image = Image.open(path)
        # exif = piexif.load(file_path)
        # image = image.resize(size)
        image.thumbnail(size)  # preserves aspect ratio
        if image.info.get('exif'):
            image.save(save_to_path,
                       quality=quality,
                       exif=image.info.get('exif'),
                       optimize=True)
        else:  # fix some bug with ebay images that apparently have no exif part
            image.save(save_to_path,
                       quality=quality,
                       # exif=image.info.get('exif'),
                       optimize=True)

    if path != save_to_path:
        os.remove(path)


def _get_images_by_plant_name(plant_name):
    # returns all image entries from photo directory tagging supplied plant name
    global photo_directory
    if not photo_directory:
        photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
        photo_directory.refresh_directory(PATH_BASE)
    images = [i for i in photo_directory.directory if
              isinstance(i.get('tag_authors_plants'), list) and plant_name in i.get('tag_authors_plants')]
    return images


def rename_plant_in_image_files(plant_name_old: str, plant_name_new: str) -> int:
    """in each image that has the old plant name tagged, switch tag to the new plant name"""
    # get the relevant images from the photo directory cache
    images = _get_images_by_plant_name(plant_name_old)
    count_modified = 0
    if not images:
        logger.info(f'No image tag to change for {plant_name_old}.')

    for image in images:
        # double check
        if plant_name_old in image['tag_authors_plants']:
            logger.info(f"Switching plant tag in image file {image['path_full_local']}")
            rename_plant_in_exif_tags(image, plant_name_old, plant_name_new)
            count_modified += 1

    # note: there's no need to upload the cache as we did modify directly in the cache above
    return count_modified

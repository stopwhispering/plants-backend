from itertools import chain
from pathlib import Path, PurePath
from typing import Tuple, List, Generator
from PIL import Image
import logging
from typing import Set

from plants import config
from plants.services.PhotoDirectory import lock_photo_directory, get_photo_directory
from plants.services.Photo import Photo
from plants.util.filename_utils import get_generated_filename, with_suffix
from plants.util.image_utils import generate_thumbnail

logger = logging.getLogger(__name__)


def generate_previewimage_get_rel_path(original_image_rel_path: PurePath) -> Path:
    """
    generates a preview photo for a plant's default photo if not exists, yet
    returns the relative path to it
    """
    # get filename of preview photo and check if that file already exists
    filename_generated = get_generated_filename(filename_original=original_image_rel_path.name,
                                                size=config.size_preview_image)

    path_full = config.path_photos_base.joinpath(original_image_rel_path)
    path_generated = config.path_generated_thumbnails.joinpath(filename_generated)

    if not path_generated.is_file():
        if not config.log_ignore_missing_image_files:
            logger.info('Preview Image: Generating the not-yet-existing preview photo.')
        generate_thumbnail(image=path_full,
                           size=config.size_preview_image,
                           path_thumbnail=config.path_generated_thumbnails)

    return config.rel_path_photos_generated.joinpath(filename_generated)


def get_thumbnail_relative_path_for_relative_path(path_relative: PurePath, size: tuple) -> Path:
    """
    returns relative path of the corresponding thumbnail for an photo file's relative path
    """
    filename_thumbnail = get_generated_filename(path_relative.name, size)
    return config.rel_path_photos_generated.joinpath(filename_thumbnail)


def get_path_for_taxon_thumbnail(filename: Path):
    return config.rel_path_photos_generated_taxon.joinpath(filename)


def get_distinct_keywords_from_image_files() -> Set[str]:
    """
    get set of all keywords from all the images in the directory
    """
    with lock_photo_directory:
        photo_directory = get_photo_directory()

        # get flattening generator and create set of distinct keywords
        keywords_nested_gen = (photo.keywords for photo in photo_directory.photos if photo.keywords)
        return set(chain.from_iterable(keywords_nested_gen))


def resizing_required(path: str, size: Tuple[int, int]) -> bool:
    """
    checks size of photo at supplied path and compares to supplied maximum size
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


def resize_image(path: Path, save_to_path: Path, size: Tuple[int, int], quality: int) -> None:
    """
    load photo at supplied path, save resized photo to other path; observes size and quality params;
    original file is finally <<deleted>>
    """
    with Image.open(path.as_posix()) as image:
        image.thumbnail(size)  # preserves aspect ratio
        if image.info.get('exif'):
            image.save(save_to_path.as_posix(),
                       quality=quality,
                       exif=image.info.get('exif'),
                       optimize=True)
        else:  # fix some bug with ebay images that apparently have no exif part
            logger.info("Saving w/o exif.")
            image.save(save_to_path.as_posix(),
                       quality=quality,
                       optimize=True)

    if path != save_to_path:
        path.unlink()  # delete file


def _get_images_by_plant_name(plant_name: str) -> Generator[Photo, None, None]:
    """
    returns generator of photo entries from photo directory tagging supplied plant name
    """
    with lock_photo_directory:
        photo_directory = get_photo_directory()
        return (p for p in photo_directory.photos if plant_name in p.plants)
    # isinstance(p.plants, list) and plant_name in p.plants]


def rename_plant_in_image_files(plant_name_old: str, plant_name_new: str) -> int:
    """
    in each photo file that has the old plant name tagged, fit tag to the new plant name
    """
    # get the relevant images from the photo directory cache
    images = _get_images_by_plant_name(plant_name_old)
    count_modified = 0
    if not images:
        logger.info(f'No photo tag to change for {plant_name_old}.')

    photo: Photo
    for photo in images:
        # double check
        if plant_name_old in photo.plants:
            logger.info(f"Switching plant tag in photo file {photo.absolute_path}")
            photo.rename_tagged_plant(plant_name_old=plant_name_old, plant_name_new=plant_name_new)
            count_modified += 1

    # note: there's no need to upload the cache as we did modify directly in the cache above
    return count_modified


def remove_files_already_existing(files: List, suffix: str) -> List[str]:
    """
    iterates over file objects, checks whether a file with that name already exists in filesystem; removes already
    existing files from files list and returns a list of already existing file names
    """
    duplicate_filenames = []
    for photo_upload in files[:]:  # need to loop on copy if we want to delete within loop
        path = config.path_original_photos_uploaded.joinpath(photo_upload.filename)
        logger.debug(f'Checking uploaded photo ({photo_upload.content_type}) to be saved as {path}.')
        if path.is_file() or with_suffix(path, suffix).is_file():
            files.remove(photo_upload)
            duplicate_filenames.append(photo_upload.filename)
            logger.warning(f'Skipping file upload (duplicate) for: {photo_upload.filename}')
    return duplicate_filenames

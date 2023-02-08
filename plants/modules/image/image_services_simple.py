from pathlib import PurePath, Path
from typing import List, Tuple
import logging

from PIL import Image

from plants import settings
from plants.modules.plant.image_dal import ImageDAL

logger = logging.getLogger(__name__)


def _original_image_file_exists(filename: str) -> bool:
    return settings.paths.path_original_photos_uploaded.joinpath(filename).is_file()


def _remove_image_from_filesystem(filename: str) -> None:
    settings.paths.path_original_photos_uploaded.joinpath(filename).unlink()


async def remove_files_already_existing(files: List, image_dal: ImageDAL) -> Tuple[list[str], list[str]]:
    """
    iterates over file objects, checks whether a file with that name already exists in filesystem and/or in database
     - if we have an orphaned file in filesystem, missing in database, it will be deleted with a messasge
     - if we have have an orphaned entry in database, missing in filesystem, it will be deleted with a messasge
     - if existent in both filesystem and db, remove it from  files list with a message
    """
    duplicate_filenames = []
    warnings = []
    for photo_upload in files[:]:  # need to loop on copy if we want to delete within loop
        # path = config.path_original_photos_uploaded.joinpath(photo_upload.filename)
        # logger.debug(f'Checking uploaded photo_file ({photo_upload.content_type}) to be saved as {path}.')
        exists_in_filesystem = _original_image_file_exists(filename=photo_upload.filename)
        exists_in_db = await image_dal.image_exists(filename=photo_upload.filename)
        if exists_in_filesystem and not exists_in_db:
            _remove_image_from_filesystem(filename=photo_upload.filename)
            logger.warning(warning := f'Found orphaned image {{photo_upload.filename}} in filesystem, '
                                      f'but not in database. Deletied image file.')
            warnings.append(warning)
        elif exists_in_db and not exists_in_filesystem:
            await image_dal.delete_image_by_filename(filename=photo_upload.filename)
            logger.warning(warning := f'Found orphaned db entry for uploaded image  {photo_upload.filename} with no '
                           f'corresponsing file. Removed db entry.')
            warnings.append(warning)
        # if path.is_file() or with_suffix(path, suffix).is_file():
        elif exists_in_filesystem and exists_in_db:
            files.remove(photo_upload)
            duplicate_filenames.append(photo_upload.filename)
            logger.warning(f'Skipping file upload (duplicate) for: {photo_upload.filename}')
    return duplicate_filenames, warnings


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
    return settings.paths.rel_path_photos_generated_taxon.joinpath(filename)


def get_relative_path(absolute_path: Path) -> PurePath:
    # todo better with .parent?
    rel_path_photos_original = settings.paths.rel_path_photos_original.as_posix()
    absolute_path_str = absolute_path.as_posix()
    return PurePath(absolute_path_str[absolute_path_str.find(rel_path_photos_original):])

from pathlib import PurePath, Path

from plants import settings
from plants.util.filename_utils import get_generated_filename


def get_thumbnail_relative_path_for_relative_path(path_relative: PurePath, size: tuple) -> Path:
    """
    returns relative path of the corresponding thumbnail for a photo_file file's relative path
    """
    filename_thumbnail = get_generated_filename(path_relative.name, size)
    return settings.paths.rel_path_photos_generated.joinpath(filename_thumbnail)


def get_absolute_path_for_generated_image(filename: str) -> Path:
    """
    returns absolute path of the corresponding thumbnail
    """
    return settings.paths.path_generated_thumbnails.joinpath(filename)
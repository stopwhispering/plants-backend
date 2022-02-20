from typing import Sequence


def with_suffix(path: str, suffix: str) -> str:
    """
    return filename or path with a suffix added
    """
    path_list = path.split('.')
    if len(path_list) >= 2:
        path_list[-2] = f'{path_list[-2]}{suffix}'
    return ".".join(path_list)


def get_generated_filename(filename_original: str, size: Sequence) -> str:
    """
    get the derivative filename of a resized image file (when creating thumbnails, a common
    naming convention is applied that adds resolution as a suffix to the filename)
    """
    suffix = f'{size[0]}_{size[1]}'
    filename_list = filename_original.split('.')
    filename_list.insert(-1, suffix)
    filename_generated = ".".join(filename_list)
    return filename_generated

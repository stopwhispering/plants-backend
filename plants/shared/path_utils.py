from pathlib import Path
from typing import Sequence


def with_suffix(path: Path, suffix: str) -> Path:
    """return filename or path with a suffix added
    """
    filename_new = path.stem + suffix + path.suffix
    return path.with_name(filename_new)


def get_generated_filename(filename_original: str, size: tuple[int, int] = None) -> str:
    """get the derivative filename of a resized photo_file file (when creating thumbnails, a common
    naming convention is applied that adds resolution as a suffix to the filename)
    """
    # todo implement with pathlib
    if not size:
        return filename_original

    suffix = f'{size[0]}_{size[1]}'
    filename_list = filename_original.split('.')
    filename_list.insert(-1, suffix)
    filename_generated = ".".join(filename_list)
    return filename_generated


def find_jpg_files(folder: Path) -> set[Path]:
    paths = list(folder.rglob('**/*.jp*g'))
    paths.extend(list(folder.rglob('**/*.JP*G')))  # on linux glob works case-sensitive!
    # we need to remove dupliates for windows
    return set(paths)


def create_if_not_exists(folders: Sequence[Path], parents: bool):
    """create folders if not exist; optionally recursively incl. parents"""
    for path in folders:
        if not path.is_dir():
            path.mkdir(parents=parents)
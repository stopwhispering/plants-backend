from glob import glob
from pathlib import Path
from typing import Sequence, Set
from os import name


def with_suffix(path: Path, suffix: str) -> Path:
    """return filename or path with a suffix added
    """
    filename_new = path.stem + suffix + path.suffix
    return path.with_name(filename_new)
    # path_list = path.as_posix().split('.')
    # if len(path_list) >= 2:
    #     path_list[-2] = f'{path_list[-2]}{suffix}'
    # return Path(".".join(path_list))


def get_generated_filename(filename_original: str, size: Sequence) -> str:
    """get the derivative filename of a resized image file (when creating thumbnails, a common
    naming convention is applied that adds resolution as a suffix to the filename)
    """
    suffix = f'{size[0]}_{size[1]}'
    filename_list = filename_original.split('.')
    filename_list.insert(-1, suffix)
    filename_generated = ".".join(filename_list)
    return filename_generated


def add_slash(path_raw: str) -> str:
    # todo do we really need this?? there must be some better way...
    if name == 'nt':
        return path_raw + '\\'
    else:
        return path_raw + r'/'


def find_jpg_files(folder: Path) -> Set[Path]:
    paths = list(folder.rglob('**/*.jp*g'))
    paths.extend(list(folder.rglob('**/*.JP*G')))  # on linux glob works case-sensitive!

    # todo remove the old glob.glob code if this never fails...
    paths_old = glob(folder.as_posix() + '/**/*.jp*g', recursive=True)
    paths_old.extend(glob(folder.as_posix() + '/**/*.JP*G', recursive=True))
    # paths_old = [Path(p) for p in paths_old]
    assert len(paths) == len(paths_old)
    # we need to remove dupliates for windows
    return set(paths)


def create_if_not_exists(folders: Sequence[Path], parents: bool):
    """create folders if not exist; optionally recursively incl. parents"""
    for path in folders:
        if not path.is_dir():
            path.mkdir(parents=parents)

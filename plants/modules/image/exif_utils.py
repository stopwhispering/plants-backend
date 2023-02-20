from pathlib import Path
from typing import List, Tuple
import logging
import os
import datetime

import pytz
from PIL import Image
import piexif
from piexif import InvalidImageDataError

logger = logging.getLogger(__name__)


def modified_date(path_to_file: Path) -> float:
    """
    tries to get the file's last modified date (in seconds)
    see http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    return path_to_file.lstat().st_mtime
    # if platform.system() == 'Windows':
    #     return os.path.getmtime(path_to_file.as_posix())
    # else:
    #     stat = os.stat(path_to_file.as_posix())
    #     return stat.st_mtime


def set_modified_date(path_to_file: Path, modified_time_seconds: float) -> None:
    """
    set file's last access and modified time
    """
    # todo pathlib
    os.utime(path_to_file.as_posix(), (modified_time_seconds, modified_time_seconds))


def decode_record_date_time(date_time_bin: bytes) -> datetime.datetime:
    """
    decode exif tag datetime to regular datetime object
    from b"YYYY:MM:DD HH:MM:SS" to datetime object
    """
    try:
        s_dt = date_time_bin.decode('utf-8')
        s_format = '%Y:%m:%d %H:%M:%S'
    except AttributeError:  # manually entered string 
        s_dt = date_time_bin
        s_format = '%Y-%m-%d'
    return datetime.datetime.strptime(s_dt, s_format)


def encode_record_date_time(dt: datetime.datetime):
    """
    encode datetime into format required by exif tag
    from datetime object to b"YYYY:MM:DD HH:MM:SS"
    """
    s_format = '%Y:%m:%d %H:%M:%S'
    s_dt = dt.strftime(s_format)
    return s_dt.encode('utf-8')


def auto_rotate_jpeg(path_image: Path, exif_dict: dict) -> None:
    """
    auto-rotates images according to exif tag; required as chrome does not display them correctly otherwise;
    applies a recompression with high quality; re-attaches the original exif files to the new file but without the
    orientation tag
    """
    if (not exif_dict
            or piexif.ImageIFD.Orientation not in exif_dict["0th"]
            or exif_dict["0th"][piexif.ImageIFD.Orientation] == 1):
        return

    img = Image.open(path_image)
    orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)

    try:
        exif_bytes = piexif.dump(exif_dict)
    except ValueError as e:
        # treat error "Given thumbnail is too large. max 64kB"
        logger.warning(f'Catched exception when auto-rotating image file: {str(e)}. Trying again after deleting '
                       'embedded thumbnail.')
        del exif_dict['thumbnail']
        exif_bytes = piexif.dump(exif_dict)

    filename = path_image.name

    if orientation == 2:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        logger.info(f'Rotating {filename} with orientation exif tag {orientation}: flip left ot right.')
    elif orientation == 3:
        img = img.rotate(180)
        logger.info(f'Rotating {filename} with orientation exif tag {orientation}: 180.')
    elif orientation == 4:
        img = img.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
        logger.info(f'Rotating {filename} with orientation exif tag {orientation}: 180 & flip left to right.')
    elif orientation == 5:
        img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        logger.info(f'Rotating {filename} with orientation exif tag {orientation}: -90 & flip left to right.')
    elif orientation == 6:
        img = img.rotate(-90, expand=True)
        logger.info(f'Rotating {filename} with orientation exif tag {orientation}: -90.')
    elif orientation == 7:
        img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
        logger.info(f'Rotating {filename} with orientation exif tag {orientation}: 90 & flip left to right.')
    elif orientation == 8:
        img = img.rotate(90, expand=True)
        logger.info(f'Rotating {filename} with orientation exif tag {orientation}: 90.')

    img.save(path_image, exif=exif_bytes, quality=90)


def decode_keywords_tag(t: tuple) -> List[str]:
    """
    decode a tuple of unicode byte integers (0..255) to a list of strings; required to get keywords into a regular
    format coming from exif tags
    """
    chars_iter = map(chr, t)
    chars = ''.join(chars_iter)
    chars = chars.replace('\x00', '')  # remove null bytes after each character
    return chars.split(';')


def encode_keywords_tag(keywords: list[str]) -> Tuple:
    """
    reverse decode_keywords_tag function
    """
    ord_list = []
    for keyword in keywords:
        ord_list_new = [ord(t) for t in keyword]
        if ord_list:
            ord_list = ord_list + [59] + ord_list_new  # add ; as separator
        else:
            ord_list = ord_list_new

    # add \x00 (0) after each element
    ord_list_final = []
    for item in ord_list:
        ord_list_final.append(item)
        ord_list_final.append(0)
    ord_list_final.append(0)
    ord_list_final.append(0)

    return tuple(ord_list_final)


def exif_dict_has_all_relevant_tags(exif_dict: dict) -> bool:
    """
    the application uses most of all three exif tags to store information; returns whether all of them
    are extant in supplied exif dict
    """
    try:
        _ = exif_dict['0th'][270]  # description
        _ = exif_dict['0th'][40094]  # keywords
        _ = exif_dict['0th'][315]  # authors (used for plants)
    except KeyError:
        return False
    return True


def read_record_datetime_from_exif_tags(absolute_path: Path) -> datetime.datetime | None:
    """
    open jpeg file and read exif tags; decode and return original record datetime
    """
    if not absolute_path:
        raise ValueError('File path not set.')

    try:
        exif_dict = piexif.load(absolute_path.as_posix())
    except InvalidImageDataError:
        logger.warning(f'Invalid Image Type Error occured when reading EXIF Tags for {absolute_path}.')
        return None
    except ValueError as e:
        raise e

    if 36867 in exif_dict["Exif"]:  # DateTimeOriginal (date and time when the original image data was generated)
        return decode_record_date_time(exif_dict["Exif"][36867])
    else:
        # get creation date from file system (todo linux has only modifed date, does this still work or abort?)
        ts = absolute_path.stat().st_ctime
        # return datetime.datetime.fromtimestamp(ts, tz=pytz.timezone('Europe/London'))
        return datetime.datetime.fromtimestamp(ts)

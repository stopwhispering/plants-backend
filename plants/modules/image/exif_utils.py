from __future__ import annotations

import datetime
import logging
import os
from typing import TYPE_CHECKING, Any

import piexif
import pytz
from PIL import Image as PilImage

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def modified_date(path_to_file: Path) -> float:
    """tries to get the file's last modified date (in seconds) see
    http://stackoverflow.com/a/39501288/1709587 for explanation."""
    return path_to_file.lstat().st_mtime


def set_modified_date(path_to_file: Path, modified_time_seconds: float) -> None:
    """Set file's last access and modified time."""
    # todo pathlib
    os.utime(path_to_file.as_posix(), (modified_time_seconds, modified_time_seconds))


def decode_record_date_time(date_time_bin: bytes) -> datetime.datetime:
    """Decode exif tag datetime to regular datetime object from b"YYYY:MM:DD HH:MM:SS"
    to datetime object."""
    try:
        s_dt = date_time_bin.decode("utf-8")
        s_format = "%Y:%m:%d %H:%M:%S"
    except AttributeError:  # manually entered string
        s_dt = date_time_bin.decode()
        s_format = "%Y-%m-%d"
    return datetime.datetime.strptime(s_dt, s_format).astimezone(
        pytz.timezone("Europe/Berlin")
    )


def encode_record_date_time(dt: datetime.datetime) -> bytes:
    """Encode datetime into format required by exif tag from datetime object to
    b"YYYY:MM:DD HH:MM:SS"."""
    s_format = "%Y:%m:%d %H:%M:%S"
    s_dt = dt.strftime(s_format)
    return s_dt.encode("utf-8")


def _auto_rotate_by_exif_flag(
    img: PilImage.Image, orientation_flag: int
) -> PilImage.Image:
    if orientation_flag == 2:
        img = img.transpose(PilImage.FLIP_LEFT_RIGHT)
        logger.info(
            f"Rotating with orientation exif tag {orientation_flag}: flip left "
            f"or right."
        )
    elif orientation_flag == 3:
        img = img.rotate(180)
        logger.info(f"Rotating with orientation exif tag {orientation_flag}: 180.")
    elif orientation_flag == 4:
        img = img.rotate(180).transpose(PilImage.FLIP_LEFT_RIGHT)
        logger.info(
            f"Rotating with orientation exif tag {orientation_flag}: 180 & flip "
            f"left to right."
        )
    elif orientation_flag == 5:
        img = img.rotate(-90, expand=True).transpose(PilImage.FLIP_LEFT_RIGHT)
        logger.info(
            f"Rotating with orientation exif tag {orientation_flag}: -90 & flip "
            f"left to right."
        )
    elif orientation_flag == 6:
        img = img.rotate(-90, expand=True)
        logger.info(f"Rotating with orientation exif tag {orientation_flag}: -90.")
    elif orientation_flag == 7:
        img = img.rotate(90, expand=True).transpose(PilImage.FLIP_LEFT_RIGHT)
        logger.info(
            f"Rotating with orientation exif tag {orientation_flag}: 90 & flip "
            f"left to right."
        )
    elif orientation_flag == 8:
        img = img.rotate(90, expand=True)
        logger.info(f"Rotating with orientation exif tag {orientation_flag}: 90.")
    return img


def auto_rotate_jpeg(path_image: Path, exif_dict: dict[str, Any]) -> None:
    """Auto-rotates images according to exif tag; required as chrome does not display
    them correctly otherwise; applies a recompression with high quality; re-attaches the
    original exif files to the new file but without the orientation tag."""
    if (
        not exif_dict
        or piexif.ImageIFD.Orientation not in exif_dict["0th"]
        or exif_dict["0th"][piexif.ImageIFD.Orientation] == 1
    ):
        return
    img = PilImage.open(path_image)
    orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)

    try:
        exif_bytes = piexif.dump(exif_dict)
    except ValueError as e:
        # treat error "Given thumbnail is too large. max 64kB"
        logger.warning(
            f"Catched exception when auto-rotating image file: {str(e)}. Trying again "
            f"after deleting embedded thumbnail."
        )
        del exif_dict["thumbnail"]
        exif_bytes = piexif.dump(exif_dict)

    img = _auto_rotate_by_exif_flag(img=img, orientation_flag=orientation)
    img.save(path_image, exif=exif_bytes, quality=90)


def encode_keywords_tag(keywords: list[str]) -> tuple[int, ...]:
    """Reverse decode_keywords_tag function."""
    ord_list: list[int] = []
    for keyword in keywords:
        ord_list_new = [ord(t) for t in keyword]
        ord_list = [*ord_list, 59, *ord_list_new] if ord_list else ord_list_new

    # add \x00 (0) after each element
    ord_list_final = []
    for item in ord_list:
        ord_list_final.append(item)
        ord_list_final.append(0)
    ord_list_final.append(0)
    ord_list_final.append(0)

    return tuple(ord_list_final)


def exif_dict_has_all_relevant_tags(exif_dict: dict[str, Any]) -> bool:
    """The application uses most of all three exif tags to store information; returns
    whether all of them are extant in supplied exif dict."""
    try:
        _ = exif_dict["0th"][270]  # description
        _ = exif_dict["0th"][40094]  # keywords
        _ = exif_dict["0th"][315]  # authors (used for plants)
    except KeyError:
        return False
    return True


def read_record_datetime_from_exif_tags(
    absolute_path: Path,
) -> datetime.datetime:
    """Open jpeg file and read exif tags; decode and return original record datetime."""
    if not absolute_path:
        raise ValueError("File path not set.")

    # try:
    exif_dict = piexif.load(absolute_path.as_posix())
    # except InvalidImageDataError:
    #     throw_exception(
    #         f"Invalid Image Type Error occured when reading EXIF Tags for "
    #         f"{absolute_path}."
    #     )

    if (
        36867 in exif_dict["Exif"]
    ):  # DateTimeOriginal (date and time when the original image data was generated)
        return decode_record_date_time(exif_dict["Exif"][36867])

    # get creation date from file system
    ts = absolute_path.stat().st_ctime
    # return datetime.datetime.fromtimestamp(ts, tz=pytz.timezone('Europe/London'))
    return datetime.datetime.fromtimestamp(ts, tz=pytz.timezone("Europe/Berlin"))

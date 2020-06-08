from PIL import Image
import logging
import os
import platform
import datetime
import piexif

logger = logging.getLogger(__name__)


def modified_date(path_to_file):
    """
    Try to get the date that a file was modified (in seconds)
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getmtime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        return stat.st_mtime  # st_mtime_ns


def set_modified_date(path_to_file, modified_time_seconds):
    # set access and modified time
    os.utime(path_to_file, (modified_time_seconds, modified_time_seconds))


def decode_record_date_time(date_time_bin: bytes):
    # from b"YYYY:MM:DD HH:MM:SS" to datetime object
    try:
        s_dt = date_time_bin.decode('utf-8')
        s_format = '%Y:%m:%d %H:%M:%S'
    except AttributeError:  # manually entered string 
        s_dt = date_time_bin
        s_format = '%Y-%m-%d'
    dt = datetime.datetime.strptime(s_dt, s_format)
    return dt


def encode_record_date_time(dt: datetime.datetime):
    # from datetime object to b"YYYY:MM:DD HH:MM:SS"
    s_format = '%Y:%m:%d %H:%M:%S'
    s_dt = dt.strftime(s_format)
    b_dt = s_dt.encode('utf-8')
    return b_dt


def dicts_to_strings(list_of_dicts: [dict]):
    results = []
    for d in list_of_dicts:
        results.append(d['key'])
    return results


def copy_exif(path_from: str, path_to: str):
    exif_dict = piexif.load(path_from)
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, path_to)


def auto_rotate_jpeg(path_image, exif_dict):
    """auto-rotates images according to exif tag; required as chrome does not display them correctly otherwise;
    applies a recompression with high quality; re-attaches the original exif files to the new file (but without the
    orientation tag)"""
    if not exif_dict \
            or piexif.ImageIFD.Orientation not in exif_dict["0th"] \
            or exif_dict["0th"][piexif.ImageIFD.Orientation] == 1:
        return

    img = Image.open(path_image)
    orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)
    exif_bytes = piexif.dump(exif_dict)
    filename = os.path.basename(path_image)

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

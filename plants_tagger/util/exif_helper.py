import os
import platform
import datetime

import piexif


def exif_dict_has_all_relevant_tags(exif_dict: dict):
    try:
        _ = exif_dict['0th'][270]  # description
        _ = exif_dict['0th'][40094]  # keywords
        _ = exif_dict['0th'][315]  # authors (used for plants)
    except KeyError:
        return False
    return True


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


def decode_record_date_time(bDateTime: bytes):
    # from b"YYYY:MM:DD HH:MM:SS" to datetime object
    try:
        s_dt = bDateTime.decode('utf-8')
        s_format = '%Y:%m:%d %H:%M:%S'
    except AttributeError:  # manually entered string 
        s_dt = bDateTime
        s_format = '%Y-%m-%d'
    dt = datetime.datetime.strptime(s_dt, s_format)
    return dt


def encode_record_date_time(dt: datetime.datetime):
    # from datetime object to b"YYYY:MM:DD HH:MM:SS"
    s_format = '%Y:%m:%d %H:%M:%S'
    s_dt = dt.strftime(s_format)
    b_dt = s_dt.encode('utf-8')
    return b_dt


def dicts_to_strings(list_of_dicts:[dict]):
    results = []
    for d in list_of_dicts:
        results.append(d['key'])
    return results


def copy_exif(path_from: str, path_to: str):
    exif_dict = piexif.load(path_from)
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, path_to)

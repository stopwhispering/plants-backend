import datetime
from typing import List
import piexif
from piexif import InvalidImageDataError
import logging

from plants_tagger.util.exif_utils import auto_rotate_jpeg, decode_record_date_time, dicts_to_strings, modified_date, \
    encode_record_date_time, set_modified_date

photo_directory = None
logger = logging.getLogger(__name__)


def read_exif_tags(file: dict):
    """reads exif info for supplied file and parses information from it (plants list etc.);
    data is directly written into the file dictionary parameter that requires at least the
    'path_full_local' key"""
    try:
        exif_dict = piexif.load(file['path_full_local'])
    except InvalidImageDataError:
        logger.warning(f'Invalid Image Type Error occured when reading EXIF Tags for {file["path_full_local"]}.')
        file.update({'tag_description': '',
                     'tag_keywords': [],
                     'tag_authors_plants': [],
                     'record_date_time': None})
        return
    # logger.debug(file['path_full_local'])

    auto_rotate_jpeg(file['path_full_local'], exif_dict)

    try:  # description
        file['tag_description'] = exif_dict['0th'][270].decode('utf-8')  # windows description/title tag
    except KeyError:
        file['tag_description'] = ''

    try:  # keywords
        file['tag_keywords'] = _decode_keywords_tag(exif_dict['0th'][40094])  # Windows Keywords Tag
        if not file['tag_keywords'][0]:  # ''
            file['tag_keywords'] = []
    except KeyError:
        file['tag_keywords'] = []

    try:  # plants (list); read from authors exif tag
        # if 315 in exif_dict['0th']:
        file['tag_authors_plants'] = exif_dict['0th'][315].decode('utf-8').split(';')  # Windows Authors Tag
        if not file['tag_authors_plants'][0]:  # ''
            file['tag_authors_plants'] = []
    except KeyError:
        file['tag_authors_plants'] = []

    try:  # record date+time
        file['record_date_time'] = decode_record_date_time(exif_dict["Exif"][36867])
    except KeyError:
        file['record_date_time'] = None


def _decode_keywords_tag(t: tuple):
    """decode a tuple of unicode byte integers (0..255) to a list of strings"""
    char_list = list(map(chr, t))
    chars = ''.join(char_list)
    chars = chars.replace('\x00', '')  # remove null bytes after each character
    keywords: List[str] = chars.split(';')
    return keywords


def encode_keywords_tag(keywords: list):
    """reverse decode_keywords_tag function"""
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


def exif_dict_has_all_relevant_tags(exif_dict: dict):
    try:
        _ = exif_dict['0th'][270]  # description
        _ = exif_dict['0th'][40094]  # keywords
        _ = exif_dict['0th'][315]  # authors (used for plants)
    except KeyError:
        return False
    return True


def write_new_exif_tags(images_data):
    for data in images_data:
        tag_descriptions = data['description'].encode('utf-8')
        list_keywords = [k['keyword'] for k in data['keywords']]
        tag_keywords = encode_keywords_tag(list_keywords)

        if list_plants := dicts_to_strings(data['plants']):
            tag_authors_plants = ';'.join(list_plants).encode('utf-8')
        else:
            tag_authors_plants = b''

        path = data['path_full_local']
        exif_dict = piexif.load(path)

        # always overwrite if image misses one of the relevant tags
        if not exif_dict_has_all_relevant_tags(exif_dict):
            modified = True
        else:
            # check if any of the tags has been changed
            modified = True if exif_dict['0th'][270] != tag_descriptions \
                        or exif_dict['0th'][40094] != tag_keywords \
                        or exif_dict['0th'][315] != tag_authors_plants else False

        if modified:
            exif_dict['0th'][270] = tag_descriptions  # windows description/title tag
            exif_dict['0th'][40094] = tag_keywords  # Windows Keywords Tag
            exif_dict['0th'][315] = tag_authors_plants  # Windows Authors Tag

            # we want to preserve the file's last-change-date
            # additionally, if image does not have a record time in exif tag,
            #    then we enter the last-changed-date there
            modified_time_seconds = modified_date(path)  # seconds
            if 36867 not in exif_dict['Exif'] or not exif_dict['Exif'][36867]:
                dt = datetime.datetime.fromtimestamp(modified_time_seconds)
                b_dt = encode_record_date_time(dt)
                exif_dict['Exif'][36867] = b_dt

            # fix some problem with windows photo editor writing exif tag in wrong format
            if exif_dict.get('GPS') and type(exif_dict['GPS'].get(11)) is bytes:
                del exif_dict['GPS'][11]
            exif_bytes = piexif.dump(exif_dict)
            # save using pillow...
            # im = Image.open(path)
            # im.save(path, "jpeg", exif=exif_bytes)
            # ...or save using piexif
            piexif.insert(exif_bytes, path)
            # reset modified time
            set_modified_date(path, modified_time_seconds)  # set access and modifide date

            # update cache in PhotoDirectory
            global photo_directory
            if photo_directory:
                photo_directory.update_image_data(data)


def rename_plant_in_exif_tags(image: dict, plant_name_old: str, plant_name_new: str):
    # we want to preserve the file's last-change-date
    modified_time_seconds = modified_date(image['path_full_local'])  # seconds

    # get a new list of plants for the image and convert it to exif tag syntax
    image['tag_authors_plants'].remove(plant_name_old)
    image['tag_authors_plants'].append(plant_name_new)
    tag_authors_plants = ';'.join(image['tag_authors_plants']).encode('utf-8')

    # load file's current exif tags and overwrite the authors tag used for saving plants
    exif_dict = piexif.load(image['path_full_local'])
    exif_dict['0th'][315] = tag_authors_plants  # Windows Authors Tag

    # update the file's exif tags physically
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, image['path_full_local'])

    # reset file's last modified date to the previous date
    set_modified_date(image['path_full_local'], modified_time_seconds)  # set access and modifide date

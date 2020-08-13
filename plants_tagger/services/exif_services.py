import datetime
import piexif
import logging

from plants_tagger.util.exif_utils import dicts_to_strings, modified_date, \
    encode_record_date_time, set_modified_date
from plants_tagger.services.PhotoDirectory import lock_photo_directory, get_photo_directory

# photo_directory = None
logger = logging.getLogger(__name__)


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
            # global photo_directory
            with lock_photo_directory:
                if p := get_photo_directory(instantiate=False):
                    p.update_image_data(data)


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

from typing import List
import piexif
import datetime
import os
from PIL import Image
import glob
import functools
import operator
import threading
import logging

import plants_tagger.config_local
from plants_tagger import config
from plants_tagger.config_local import folder_root_original_images

from plants_tagger.util.exif_helper import exif_dict_has_all_relevant_tags, modified_date, set_modified_date, \
    decode_record_date_time, encode_record_date_time, dicts_to_strings, auto_rotate_jpeg

PATH_GEN = plants_tagger.config_local.rel_folder_photos_generated
PATH_SUB = r"localService\photos"
REL_FOLDER_PHOTOS_ORIGINAL = plants_tagger.config_local.rel_folder_photos_original

lock_photo_directory = threading.RLock()
photo_directory = None
logger = logging.getLogger(__name__)

FOLDER_ROOT = plants_tagger.config_local.folder_root_original_images
FOLDER_GENERATED = os.path.join(plants_tagger.config_local.path_frontend_temp,
                                plants_tagger.config_local.rel_folder_photos_generated)


def generate_previewimage_get_rel_path(original_image_rel_path_raw):
    """generates a preview image for a plant's default image if not exists, yet; returns the relative path to it"""
    # get filename of preview image and check if that file already exists

    if os.name == 'nt':  # handle forward- and backslash for linux/windows systems
        original_image_rel_path = original_image_rel_path_raw.replace('/', '\\')
    else:
        original_image_rel_path = original_image_rel_path_raw.replace('\\', '/')

    filename_original = os.path.basename(original_image_rel_path)
    filename_generated = _util_get_generated_filename(filename_original,
                                                      size=config.size_preview_image)
    # todo: use PhotoDirectory list
    # path_full = os.path.join(plants_tagger.config_local.path_frontend_temp, original_image_rel_path)
    path_full = os.path.join(plants_tagger.config_local.path_photos, original_image_rel_path)
    # path_generated = os.path.join(plants_tagger.config_local.path_frontend_temp,
    #                               plants_tagger.config_local.rel_folder_photos_generated, filename_generated)
    # logger.debug(f"Preview Image Path Full of Original Image: {path_full}")
    path_generated = os.path.join(plants_tagger.config_local.path_photos,
                                  plants_tagger.config_local.subfolder_generated, filename_generated)
    # logger.debug(f"Preview Image Path Generated: {path_generated}")
    # create the preview image if not exists
    if not os.path.isfile(path_generated):
        logger.info('Preview Image: Generating the not-yet-existing preview image.')
        generate_thumbnail(path_basic_folder=plants_tagger.config_local.path_frontend_temp,
                           path_image=path_full,
                           size=config.size_preview_image)

    # return webapp-relative path to preview image
    rel_path = os.path.join(plants_tagger.config_local.rel_folder_photos_generated, filename_generated)
    # logger.debug(f"Preview Image relative path: {rel_path}")
    return rel_path


def generate_thumbnail(path_basic_folder: str,
                       path_image: str,
                       size: tuple = (100, 100)):
    """ generates a resized variant of an image; returns the full local path"""
    logger.debug(f'generating resized image of {path_image} in size {size}.')
    suffix = f'{size[0]}_{size[1]}'
    if not os.path.isfile(path_image):
        logger.error(f"Original Image of default image does not exist. Can't generate thumbnail. {path_image}")
        return
    im = Image.open(path_image)

    # there's a bug in chrome: it's not respecting the orientation exif (unless directly opened in chrome)
    # therefore hard-rotate thumbnail according to that exif tag
    # for orientation in ExifTags.TAGS.keys():
    #     if ExifTags.TAGS[orientation] == 'Orientation':
    #         break

    # noinspection PyProtectedMember
    exif_obj = im._getexif()
    if exif_obj:  # the image might have no exif-tags
        # noinspection PyProtectedMember
        exif = dict(im._getexif().items())
        if piexif.ImageIFD.Orientation in exif:
            if exif[piexif.ImageIFD.Orientation] == 3:
                im = im.rotate(180, expand=True)
            elif exif[piexif.ImageIFD.Orientation] == 6:
                im = im.rotate(270, expand=True)
            elif exif[piexif.ImageIFD.Orientation] == 8:
                im = im.rotate(90, expand=True)

    im.thumbnail(size)
    filename_image = os.path.basename(path_image)
    filename_thumb_list = filename_image.split('.')
    # noinspection PyTypeChecker
    filename_thumb_list.insert(-1, suffix)
    filename_thumb = ".".join(filename_thumb_list)
    path_save = os.path.join(path_basic_folder, PATH_GEN, filename_thumb)
    im.save(path_save, "JPEG")

    # thumbnails don't require any exif tags
    # exif_dict = piexif.load(path)
    # exif_bytes = piexif.dump(exif_dict)
    # piexif.insert(exif_bytes, path_new)

    return path_save


def decode_keywords_tag(t: tuple):
    """decode a tuple of unicode byte integers (0..255) to a list of strings"""
    char_list = list(map(chr, t))
    chars = ''.join(char_list)
    chars = chars.replace('\x00', '')  # remove null bytes after each character
    keywords: List[str] = chars.split(';')
    return keywords


def _util_get_generated_filename(filename_original: str, size: tuple):
    suffix = f'{size[0]}_{size[1]}'
    filename_list = filename_original.split('.')
    filename_list.insert(-1, suffix)
    filename_generated = ".".join(filename_list)
    return filename_generated


class PhotoDirectory:
    directory = None

    def __init__(self, root_folder):
        self.root_folder = root_folder

    def refresh_directory(self, path_basic_folder):
        logger.info('Re-reading exif files from Photos Folder.')
        self._scan_files(self.root_folder)
        self._get_files_already_generated(FOLDER_GENERATED)
        self._read_exif_tags_all_images()
        self._generate_images(path_basic_folder)

    def _scan_files(self, folder):
        """read all image files and create a list of dicts (one dict for each file)"""
        paths = glob.glob(folder + '/**/*.jp*g', recursive=True)
        paths.extend(glob.glob(folder + '/**/*.JP*G', recursive=True))  # on linux glob works case-sensitive!
        logger.info(f"Scanned through originals folder. Found {len(paths)} image files.")
        self.directory = [{'path_full_local': path_full,
                           'filename': os.path.basename(path_full)} for path_full in paths]

    def _get_files_already_generated(self, folder):
        """returns a list of already-generated file derivatives (thumbnails & resized)"""
        paths = glob.glob(folder + '/**/*.jp*g', recursive=True)
        paths.extend(glob.glob(folder + '/**/*.JP*G', recursive=True))  # on linux glob works case-sensitive!
        self.files_already_generated = [os.path.basename(path_full) for path_full in paths]

    def _generated_file_exists(self, filename_generated: str):
        if filename_generated in self.files_already_generated:
            return True
        else:
            return False

    def _read_exif_tags_all_images(self):
        """reads exif info for each original file and parses information from it (plants list etc.), adds these
        information to directory (i.e. to the list of dicts (one dict for each image file))"""
        logger.info(f"Starting to parse EXIF Tags of {len(self.directory)} files")
        for file in self.directory:
            read_exif_tags(file)

    def _generate_images(self, path_basic_folder: str):
        """generates image derivatives (resized & thumbnail) for each original image file if not already exists;
        adds relative paths to these generated images to directory (i.e. to the list of dicts (one dict for each
        image file))"""
        for file in self.directory:

            # generate a thumbnail...
            file['filename_thumb'] = _util_get_generated_filename(file['filename'], size=config.size_thumbnail_image)
            if not self._generated_file_exists(file['filename_thumb']):
                _ = generate_thumbnail(path_basic_folder,
                                       file['path_full_local'],
                                       config.size_thumbnail_image)

            file['path_thumb'] = os.path.join(PATH_GEN, file['filename_thumb'])
            file['path_original'] = file['path_full_local'][file['path_full_local'].find(REL_FOLDER_PHOTOS_ORIGINAL):]

    def get_all_plants(self):
        """returns all the plants that are depicted in at least one image (i.e. at least one exif tag plant
        list) in form of list of dicts"""
        if not self.directory:
            return []
        plants_list_list = [file['tag_authors_plants'] for file in self.directory]
        plants_list = functools.reduce(operator.add, plants_list_list)
        plants = list(set(plants_list))
        plants_dicts = [{'key': plant} for plant in plants]
        return plants_dicts

    def update_image_data(self, photo):
        # find the directory entry for the changed image (the full original path acts as a kind of unique key here)
        directory_entries = [x for x in self.directory if x['path_full_local'] == photo['path_full_local']]
        if not directory_entries or len(directory_entries) != 1:
            logger.error(f"Can't update photo directory cache: Unique entry for changed image not found: "
                         f"{photo['path_full_local']}")
            return
        logger.info(f'Updating changed image in PhotoDirectory Cache: {photo["path_full_local"]}')
        directory_entries[0]['tag_keywords'] = [k['key'] for k in photo['keywords']]
        directory_entries[0]['tag_authors_plants'] = [p['key'] for p in photo['plants']]
        directory_entries[0]['tag_description'] = photo['description']

    def remove_image_from_directory(self, photo):
        # find the directory entry for the deleted image (the full original path acts as a kind of unique key here)
        directory_entries = [x for x in self.directory if x['path_full_local'] == photo['path_full_local']]
        if not directory_entries or len(directory_entries) != 1:
            logger.error(f"Can't delete photo directory cache: Unique entry for deleted image not found: "
                         f"{photo['path_full_local']}")
            return
        self.directory.remove(directory_entries[0])
        logger.info(f'Removed deleted image from PhotoDirectory Cache.')


def read_exif_tags(file):
    """reads exif info for supplied file and parses information from it (plants list etc.);
    data is directly written into the file dictionary parameter that requires at least the
    'path_full_local' key"""
    exif_dict = piexif.load(file['path_full_local'])
    # logger.debug(file['path_full_local'])

    auto_rotate_jpeg(file['path_full_local'], exif_dict)

    try:  # description
        file['tag_description'] = exif_dict['0th'][270].decode('utf-8')  # windows description/title tag
    except KeyError:
        file['tag_description'] = ''

    try:  # keywords
        file['tag_keywords'] = decode_keywords_tag(exif_dict['0th'][40094])  # Windows Keywords Tag
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


def get_plants_data(directory):
    """extracts information from the directory that is relevant for the frontend;
    returns list of dicts (just like directory)"""
    plants_data = [
        {"url_small": file['path_thumb'] if 'path_thumb' in file else '',
         "url_original": file['path_original'] if 'path_original' in file else '',
         "keywords": file['tag_keywords'],
         "plants": file['tag_authors_plants'],
         "description": file['tag_description'] if 'tag_description' in file else '',
         "filename": file['filename'] if 'filename' in file else '',
         "path_full_local": file['path_full_local'],
         "record_date_time": file['record_date_time']
         } for file in directory]
    return plants_data


def get_exif_tags_for_folder(path_basic_folder: str):
    """get list of image dicts; uses global photo directory object, initialized only
    at first time after server (re-)start"""
    with lock_photo_directory:
        global photo_directory
        if not photo_directory:
            photo_directory = PhotoDirectory(folder_root_original_images)
            photo_directory.refresh_directory(path_basic_folder)
            # photo_directory._read_exif_tags()
            # photo_directory._generate_images(path_basic_folder)
        # plants_data = photo_directory.get_plants_data(photo_directory.directory)
        plants_data = get_plants_data(photo_directory.directory)
        plants_unique = photo_directory.get_all_plants()
    return plants_data, plants_unique


def encode_keywords_tag(l: list):
    """reverse decode_keywords_tag function"""
    ord_list = []
    for keyword in l:
        ord_list_new = [ord(t) for t in keyword]
        if ord_list:
            ord_list = ord_list + [59] + ord_list_new  # add ; as separator
        else:
            ord_list = ord_list_new

    # add \x00 (0) after each element
    # todo: better to it with something like encode(utf-8)?
    ord_list_final = []
    for item in ord_list:
        ord_list_final.append(item)
        ord_list_final.append(0)
    ord_list_final.append(0)
    ord_list_final.append(0)

    return tuple(ord_list_final)


def write_new_exif_tags(images_data, temp: bool = False):
    for data in images_data:
        tag_descriptions = data['description'].encode('utf-8')
        if temp:
            # from list of dicts to list of str
            list_keywords = dicts_to_strings(data['keywords'])
            list_plants = dicts_to_strings(data['plants'])
        else:
            list_keywords = data['keywords']
            list_plants = data['plants']

        tag_keywords = encode_keywords_tag(list_keywords)
        # tag_authors_plants = encode_keywords_tag(data['plants'])
        if list_plants:
            tag_authors_plants = ';'.join(list_plants).encode('utf-8')
        else:
            tag_authors_plants = b''

        # path = os.path.join(PATH_MAIN, PATH_SUB, data['filename'])
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
            # if exif_dict['0th'][270] != tag_descriptions\
            #     or exif_dict['0th'][40094] != tag_keywords\
            #         or ((315 in exif_dict['0th'] and exif_dict['0th'][315] != tag_authors_plants and tag_authors_
            #         plants)
            #             or (315 in exif_dict['0th'] and not tag_authors_plants)
            #             or (315 not in exif_dict['0th'] and tag_authors_plants)):
        if modified:
            exif_dict['0th'][270] = tag_descriptions  # windows description/title tag
            exif_dict['0th'][40094] = tag_keywords  # Windows Keywords Tag
            # if tag_authors_plants:
            exif_dict['0th'][315] = tag_authors_plants  # Windows Autoren Tag
            # elif 315 in exif_dict['0th']:
            #     del exif_dict['0th'][315]

            # we want to preserve the file's last-change-date
            # additionally, if image does not have a record time in exif tag,
            #    then we enter the last-changed-date there
            modified_time_seconds = modified_date(path)  # seconds
            if 36867 not in exif_dict['Exif'] or not exif_dict['Exif'][36867]:
                dt = datetime.datetime.fromtimestamp(modified_time_seconds)
                b_dt = encode_record_date_time(dt)
                exif_dict['Exif'][36867] = b_dt

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

from typing import List, Tuple
import piexif
import datetime
import os
from PIL import Image
import glob
import functools
import operator
import threading
import logging
from typing import Set
from piexif import InvalidImageDataError

import plants_tagger.config_local
import plants_tagger.services.os_paths
from plants_tagger import config
from plants_tagger.config_local import PATH_BASE
from plants_tagger.services.os_paths import REL_PATH_PHOTOS_ORIGINAL, REL_PATH_PHOTOS_GENERATED, \
    PATH_GENERATED_THUMBNAILS, PATH_ORIGINAL_PHOTOS
from plants_tagger.util.exif import modified_date, set_modified_date, \
    decode_record_date_time, encode_record_date_time, dicts_to_strings, auto_rotate_jpeg

lock_photo_directory = threading.RLock()
photo_directory = None
logger = logging.getLogger(__name__)
NULL_DATE = datetime.date(1900, 1, 1)


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

    path_full = os.path.join(plants_tagger.services.os_paths.PATH_PHOTOS_BASE, original_image_rel_path)
    path_generated = os.path.join(PATH_GENERATED_THUMBNAILS, filename_generated)
    if not os.path.isfile(path_generated):
        logger.info('Preview Image: Generating the not-yet-existing preview image.')
        generate_thumbnail(path_basic_folder=plants_tagger.config_local.PATH_BASE,
                           path_image=path_full,
                           size=config.size_preview_image)

    rel_path = os.path.join(plants_tagger.services.os_paths.REL_PATH_PHOTOS_GENERATED, filename_generated)
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
    _rotate_if_required(im, exif_obj)

    im.thumbnail(size)
    filename_image = os.path.basename(path_image)
    filename_thumb_list = filename_image.split('.')
    # noinspection PyTypeChecker
    filename_thumb_list.insert(-1, suffix)
    filename_thumb = ".".join(filename_thumb_list)
    path_save = os.path.join(path_basic_folder, REL_PATH_PHOTOS_GENERATED, filename_thumb)
    im.save(path_save, "JPEG")

    # thumbnails don't require any exif tags
    # exif_dict = piexif.load(path)
    # exif_bytes = piexif.dump(exif_dict)
    # piexif.insert(exif_bytes, path_new)

    return path_save


def _rotate_if_required(image, exif_obj):
    """rotate image if exif file has a rotate directive"""
    if exif_obj:  # the image might have no exif-tags
        # noinspection PyProtectedMember
        exif = dict(image._getexif().items())
        if piexif.ImageIFD.Orientation in exif:
            if exif[piexif.ImageIFD.Orientation] == 3:
                _ = image.rotate(180, expand=True)
            elif exif[piexif.ImageIFD.Orientation] == 6:
                _ = image.rotate(270, expand=True)
            elif exif[piexif.ImageIFD.Orientation] == 8:
                _ = image.rotate(90, expand=True)
    return image


def decode_keywords_tag(t: tuple):
    """decode a tuple of unicode byte integers (0..255) to a list of strings"""
    char_list = list(map(chr, t))
    chars = ''.join(char_list)
    chars = chars.replace('\x00', '')  # remove null bytes after each character
    keywords: List[str] = chars.split(';')
    return keywords


def get_thumbnail_relative_path_for_relative_path(path_relative: str, size: tuple):
    filename = os.path.basename(path_relative)
    filename_thumbnail = _util_get_generated_filename(filename, size)
    path_relative_thumbnail = os.path.join(REL_PATH_PHOTOS_GENERATED, filename_thumbnail)
    return path_relative_thumbnail


def _util_get_generated_filename(filename_original: str, size: tuple):
    suffix = f'{size[0]}_{size[1]}'
    filename_list = filename_original.split('.')
    filename_list.insert(-1, suffix)
    filename_generated = ".".join(filename_list)
    return filename_generated


class PhotoDirectory:
    directory = None
    latest_image_dates = {}

    def __init__(self, root_folder: str = PATH_ORIGINAL_PHOTOS):
        self.root_folder = root_folder

    def refresh_directory(self, path_basic_folder: str = PATH_BASE):
        logger.info('Re-reading exif files from Photos Folder.')
        self._scan_files(self.root_folder)
        self._get_files_already_generated(PATH_GENERATED_THUMBNAILS)
        self._read_exif_tags_all_images()
        self._generate_images(path_basic_folder)
        self._read_latest_image_dates()

    def _scan_files(self, folder):
        """read all image files and create a list of dicts (one dict for each file)"""
        paths = glob.glob(folder + '/**/*.jp*g', recursive=True)
        paths.extend(glob.glob(folder + '/**/*.JP*G', recursive=True))  # on linux glob works case-sensitive!
        # can't embed exif tag in png files
        # paths.extend(glob.glob(folder + '/**/*.PNG', recursive=True))
        # paths.extend(glob.glob(folder + '/**/*.png', recursive=True))
        paths = list(set(paths))  # on windows, on the other hand, the extension would produce duplicates...
        logger.info(f"Scanned through originals folder. Found {len(paths)} image files.")
        self.directory = [{'path_full_local': path_full,
                           'filename': os.path.basename(path_full)} for path_full in paths]

    def _get_files_already_generated(self, folder):
        """returns a list of already-generated file derivatives (thumbnails & resized)"""
        paths = glob.glob(folder + '/**/*.jp*g', recursive=True)
        paths.extend(glob.glob(folder + '/**/*.JP*G', recursive=True))  # on linux glob works case-sensitive!
        paths = list(set(paths))
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

            file['path_thumb'] = os.path.join(REL_PATH_PHOTOS_GENERATED, file['filename_thumb'])
            file['path_original'] = file['path_full_local'][file['path_full_local'].find(REL_PATH_PHOTOS_ORIGINAL):]

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
        directory_entries[0]['tag_keywords'] = [k['keyword'] for k in photo['keywords']]
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

    def _read_latest_image_dates(self):
        """called when refreshing photo directory; reads latest image date for all plants; contains
        only plants that have at least one image"""
        self.latest_image_dates = {}

        for image in self.directory:
            for p in image['tag_authors_plants']:
                try:
                    if p not in self.latest_image_dates or self.latest_image_dates[p] < image['record_date_time']:
                        self.latest_image_dates[p] = image['record_date_time']
                except TypeError:
                    pass

    def get_latest_date_per_plant(self, plant_name: str):
        """called by plants resource. returns latest image record date for supplied plant_name"""
        # if no image at all, use a very early date as null would sort them after late days in ui5 sorters
        # (in ui5 formatter, we will format the null_date as an empty string)
        return self.latest_image_dates.get(plant_name, NULL_DATE)


def read_exif_tags(file):
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
        {"url_small": file.get('path_thumb') or '',
         "url_original": file.get('path_original') or '',
         "keywords": file['tag_keywords'],
         "plants": file['tag_authors_plants'],
         "description": file.get('tag_description') or '',
         "filename": file['filename'] if 'filename' in file else '',
         "path_full_local": file['path_full_local'],
         "record_date_time": file['record_date_time']
         } for file in directory]
    return plants_data


def get_exif_tags_for_folder():
    """get list of image dicts; uses global photo directory object, initialized only
    at first time after server (re-)start"""
    with lock_photo_directory:
        global photo_directory
        if not photo_directory:
            photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
            photo_directory.refresh_directory(PATH_BASE)
        plants_data = get_plants_data(photo_directory.directory)
        plants_unique = photo_directory.get_all_plants()
    return plants_data, plants_unique


def get_distinct_keywords_from_image_files() -> Set[str]:
    """get set of all keywords from all the images in the directory"""
    with lock_photo_directory:
        global photo_directory
        if not photo_directory:
            photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
            photo_directory.refresh_directory(PATH_BASE)

        # get list of lists of strings, flatten that nested list and return the distinct keywords as set
        keywords_nested_list = [file.get('tag_keywords') for file in photo_directory.directory]
        keywords_nested_list = [li for li in keywords_nested_list if li]  # remove None's
        keywords_list = functools.reduce(operator.concat, keywords_nested_list)
        return set(keywords_list)


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


def resizing_required(path, size):
    with Image.open(path) as image:  # only works with path, not file object
        # image = Image.open(file_obj)
        x, y = image.size
    if x > size[0]:
        y = int(max(y * size[0] / x, 1))
        x = int(size[0])
    if y > size[1]:
        x = int(max(x * size[1] / y, 1))
        y = int(size[1])
    size = x, y
    return size != image.size


def resize_image(path: str, save_to_path: str, size: Tuple[int, int], quality: int):
    with Image.open(path) as image:
        # image = Image.open(path)
        # exif = piexif.load(file_path)
        # image = image.resize(size)
        image.thumbnail(size)  # preserves aspect ratio
        image.save(save_to_path,
                   quality=quality,
                   exif=image.info.get('exif'),
                   optimize=True)
    if path != save_to_path:
        os.remove(path)


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


def _get_images_by_plant_name(plant_name):
    # returns all image entries from photo directory tagging supplied plant name
    global photo_directory
    if not photo_directory:
        photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
        photo_directory.refresh_directory(PATH_BASE)
    images = [i for i in photo_directory.directory if
              isinstance(i.get('tag_authors_plants'), list) and plant_name in i.get('tag_authors_plants')]
    return images


def rename_plant_in_exif_tags(plant_name_old: str, plant_name_new: str) -> int:
    """in each image that has the old plant name tagged, switch tag to the new plant name"""
    # get the relevant images from the photo directory cache
    images = _get_images_by_plant_name(plant_name_old)
    count_modified = 0
    if not images:
        logger.info(f'No image tag to change for {plant_name_old}.')

    for image in images:
        # double check
        if plant_name_old in image['tag_authors_plants']:

            # we want to preserve the file's last-change-date
            logger.info(f"Switching plant tag in image file {image['path_full_local']}")
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
            count_modified += 1

    # note: there's no need to upload the cache as we did modify directly in the cache above
    return count_modified


def exif_dict_has_all_relevant_tags(exif_dict: dict):
    try:
        _ = exif_dict['0th'][270]  # description
        _ = exif_dict['0th'][40094]  # keywords
        _ = exif_dict['0th'][315]  # authors (used for plants)
    except KeyError:
        return False
    return True

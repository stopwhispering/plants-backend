import functools
import glob
import operator
import os
import logging
import datetime
import threading
from typing import Optional, Dict

from plants_tagger import config
from plants_tagger.config_local import PATH_BASE
from plants_tagger.models.entities import ImageInfo
from plants_tagger.util.exif_utils import read_exif_tags
from plants_tagger.util.filename_utils import get_generated_filename
from plants_tagger.util.image_utils import generate_thumbnail
from plants_tagger.services.os_paths import PATH_ORIGINAL_PHOTOS, PATH_GENERATED_THUMBNAILS, \
    REL_PATH_PHOTOS_GENERATED, REL_PATH_PHOTOS_ORIGINAL

logger = logging.getLogger(__name__)
NULL_DATE = datetime.date(1900, 1, 1)


class PhotoDirectory:
    directory = None
    latest_image_dates: Dict[str, ImageInfo] = {}

    def __init__(self, root_folder: str = PATH_ORIGINAL_PHOTOS):
        self.root_folder = root_folder

    def refresh_directory(self, path_basic_folder: str = PATH_BASE):
        logger.info('Re-reading exif files from Photos Folder.')
        self._scan_files(self.root_folder)
        self._get_files_already_generated(PATH_GENERATED_THUMBNAILS)
        self._read_exif_tags_all_images()
        self._generate_images(path_basic_folder)
        self._read_latest_image_dates()
        return self

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
            file['filename_thumb'] = get_generated_filename(file['filename'], size=config.size_thumbnail_image)
            if not self._generated_file_exists(file['filename_thumb']):
                _ = generate_thumbnail(image=file['path_full_local'],
                                       size=config.size_thumbnail_image,
                                       path_thumbnail=os.path.join(path_basic_folder, REL_PATH_PHOTOS_GENERATED))

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
                    if p not in self.latest_image_dates or self.latest_image_dates[p].date < image['record_date_time']:
                        self.latest_image_dates[p] = ImageInfo(date=image['record_date_time'],
                                                               path=image['path_original'],
                                                               path_thumb=image['path_thumb'])
                except TypeError:
                    pass

    def get_latest_date_per_plant(self, plant_name: str) -> ImageInfo:
        """called by plants resource. returns latest image record date for supplied plant_name"""
        # if no image at all, use a very early date as null would sort them after late days in ui5 sorters
        # (in ui5 formatter, we will format the null_date as an empty string)
        return self.latest_image_dates.get(plant_name)


lock_photo_directory = threading.RLock()
photo_directory: Optional[PhotoDirectory] = None


def get_photo_directory(instantiate=True) -> PhotoDirectory:
    global photo_directory
    if not photo_directory and instantiate:
        photo_directory = PhotoDirectory().refresh_directory()
    return photo_directory

import glob
import os
import logging
import datetime
import threading
from typing import Optional, Dict, List

from plants.models.entities import ImageInfo, PhotoFileExt, KeywordImageTagExt, PlantImageTagExt
from plants.services.Photo import Photo
from plants.services.os_paths import PATH_ORIGINAL_PHOTOS, PATH_GENERATED_THUMBNAILS

logger = logging.getLogger(__name__)
NULL_DATE = datetime.date(1900, 1, 1)


class PhotoDirectory:
    """"cache for photo files metadata"""

    def __init__(self, root_folder: str = PATH_ORIGINAL_PHOTOS):
        self.root_folder: str = root_folder
        self.latest_image_dates: Dict[str, ImageInfo] = {}
        self.photos: List[Photo] = []

    def refresh_directory(self):
        """
        refreshing photo files metadata from their exif tags
        """
        logger.info('Re-reading exif files from Photos Folder.')
        self._scan_files(self.root_folder)
        self._get_files_already_generated(PATH_GENERATED_THUMBNAILS)
        self._read_exif_tags_all_images()
        self._generate_images()
        self._read_latest_image_dates()
        return self

    def _scan_files(self, folder):
        """read all image files and create a list of dicts (one dict for each file)"""
        paths = glob.glob(folder + '/**/*.jp*g', recursive=True)
        paths.extend(glob.glob(folder + '/**/*.JP*G', recursive=True))  # on linux glob works case-sensitive!
        paths = set(paths)  # on windows, on the other hand, the extension would produce duplicates...
        logger.info(f"Scanned through originals folder. Found {len(paths)} image files.")
        self.photos = [Photo(path_full_local=path_full,
                             filename=os.path.basename(path_full)) for path_full in paths]

    def _get_files_already_generated(self, folder):
        """returns a list of already-generated file derivatives (thumbnails & resized)"""
        paths = glob.glob(folder + '/**/*.jp*g', recursive=True)
        paths.extend(glob.glob(folder + '/**/*.JP*G', recursive=True))  # on linux glob works case-sensitive!
        paths = list(set(paths))
        self.files_already_generated = [os.path.basename(path_full) for path_full in paths]

    def _read_exif_tags_all_images(self):
        """reads exif info for each original file and parses information from it (plants list etc.), adds these
        information to directory (i.e. to the list of dicts (one dict for each image file))"""
        logger.info(f"Starting to parse EXIF Tags of {len(self.photos)} files")
        for photo in self.photos:
            photo.parse_exif_tags()

    def _generate_images(self):
        """generates image derivatives (resized & thumbnail) for each original image file if not already exists;
        adds relative paths to these generated images to directory (i.e. to the list of dicts (one dict for each
        image file))"""
        for photo in self.photos:
            photo.generate_thumbnails(self.files_already_generated)

    def get_photo(self, path_full_local: str) -> Optional[Photo]:
        """
        get photo instance by path_full_local
        """
        # find (first) object in photos directory without iterating through all or creating new list
        return next((p for p in self.photos if p.path_full_local == path_full_local), None)

    def remove_image_from_directory(self, photo: Photo) -> None:
        """
        find the directory entry for the image and remove it; physical deletion of the file
        is handled elsewhere; the full original path acts as key here
        """
        # find (first) object in photos directory without iterating through all or creating list
        if photo not in self.photos:
            logger.error(f"Can't delete from photo directory cache: Unique entry for deleted image not found.")
        else:
            self.photos.remove(photo)
            logger.info(f'Removed deleted image from PhotoDirectory Cache.')

    def _read_latest_image_dates(self) -> None:
        """
        called when refreshing photo directory; reads latest image date for all plants; contains
        only plants that have at least one image
        """
        self.latest_image_dates = {}
        for photo in self.photos:
            for p in photo.tag_authors_plants:
                try:
                    if p not in self.latest_image_dates or self.latest_image_dates[p].date < photo.record_date_time:
                        self.latest_image_dates[p] = ImageInfo(date=photo.record_date_time,
                                                               path=photo.path_original,
                                                               path_thumb=photo.path_thumb)
                except TypeError:
                    pass

    def get_latest_date_per_plant(self, plant_name: str) -> ImageInfo:
        """called by plants resource. returns latest image record date for supplied plant_name"""
        return self.latest_image_dates.get(plant_name)

    def get_photo_files_ext(self) -> List[PhotoFileExt]:
        """
        extracts photo metadata and converts some keys as required in frontend
        """
        with lock_photo_directory:
            return [PhotoFileExt(
                    path_thumb=photo.path_thumb,
                    path_original=photo.path_original,
                    keywords=[KeywordImageTagExt(keyword=k) for k in photo.tag_keywords],
                    plants=[PlantImageTagExt(key=p, text=p) for p in photo.tag_authors_plants],
                    # get rid of annoying camera default image description
                    description='' if photo.tag_description.strip() == 'SONY DSC' else photo.tag_description,
                    filename=photo.filename or '',
                    path_full_local=photo.path_full_local,
                    record_date_time=photo.record_date_time
                    ) for photo in self.photos]


lock_photo_directory = threading.RLock()
photo_directory: Optional[PhotoDirectory] = None


def get_photo_directory(instantiate=True) -> PhotoDirectory:
    global photo_directory
    if not photo_directory and instantiate:
        photo_directory = PhotoDirectory().refresh_directory()
    return photo_directory

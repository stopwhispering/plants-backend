import logging
import datetime
import threading
from pathlib import Path
from typing import Optional, Dict, List

from plants import config
from plants.services.Photo import Photo
from plants.services.image_info import ImageInfo
from plants.services.photo_file_access import PhotoFileAccess
from plants.services.photo_file_access_local_storage import PhotoFileAccessLocalStorage

logger = logging.getLogger(__name__)
NULL_DATE = datetime.date(1900, 1, 1)


class PhotoDirectory:
    """"cache for photo files metadata"""

    def __init__(self,
                 file_access: PhotoFileAccess,
                 root_folder: Path = config.path_original_photos):
        self.root_folder: Path = root_folder
        self.latest_image_dates: Dict[str, ImageInfo] = {}
        self.photos: List[Photo] = []
        self.files_already_generated: list[str] = []

        self.file_access = file_access

    def refresh_directory(self):
        """
        refreshing photo files metadata
        """
        logger.info('Re-reading photos list.')
        self.photos = self.file_access.query_photos()
        self.files_already_generated = self.file_access.get_generated_files()
        self._generate_images()
        return self

    def _generate_images(self):
        # todo move to file upload and to new 'repair function'
        """generates photo derivatives (resized & thumbnail) for each original photo file if not already exists;
        adds relative paths to these generated images to directory (i.e. to the list of dicts (one dict for each
        photo file))"""
        for photo in self.photos:
            photo.generate_thumbnails(self.files_already_generated)

    def get_photo(self, absolute_path: Path) -> Optional[Photo]:
        """
        get photo instance by absolute path
        """
        # find (first) object in photos directory without iterating through all or creating new list
        return next((p for p in self.photos if p.absolute_path == absolute_path), None)

    def remove_image_from_directory(self, photo: Photo) -> None:
        """
        find the directory entry for the photo and remove it; physical deletion of the file
        is handled elsewhere
        """
        # find (first) object in photos directory without iterating through all or creating list
        if photo not in self.photos:
            logger.error(f"Can't remove from photo directory cache: not found.")
        else:
            self.photos.remove(photo)
            logger.info(f'Removed photo from PhotoDirectory Cache.')

    def get_latest_date_per_plant(self, plant_name: str) -> ImageInfo:
        """called by plants resource. returns latest photo record date for supplied plant_name"""
        return self.latest_image_dates.get(plant_name)

    def get_photo_files(self, plant_name: str = None) -> List[Photo]:
        """
        return photo file metadata, optionally filtered by plant_name
        """
        photo_files = self.photos if not plant_name else [p for p in self.photos if plant_name in p.plants]
        return photo_files

    def get_photo_files_untagged(self) -> List[Photo]:
        """
        return photo file metadata for photos that have no plants tagged, yet
        """
        photo_files = [p for p in self.photos if not p.plants]
        return photo_files


lock_photo_directory = threading.RLock()
photo_directory: Optional[PhotoDirectory] = None


def get_photo_directory(instantiate=True) -> PhotoDirectory:
    global photo_directory
    if not photo_directory and instantiate:
        # todo switch to db / make dependency
        file_access: PhotoFileAccess = PhotoFileAccessLocalStorage(path_original_photos=config.path_original_photos,
                                                                   path_derived_photos=config.path_generated_thumbnails)
        photo_directory = PhotoDirectory(file_access=file_access).refresh_directory()
    return photo_directory

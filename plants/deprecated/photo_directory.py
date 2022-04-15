import datetime
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import List, Iterable, NamedTuple
import logging
import threading
from typing import Optional

from sqlalchemy.orm import Session

from plants import config
from plants.models.image_models import Image
from plants.services.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.services.image_services_simple import get_filename_thumb, get_relative_path_thumb, get_relative_path
from plants.util.filename_utils import find_jpg_files
from plants.util.image_utils import generate_thumbnail

logger = logging.getLogger(__name__)


class PhotoDirectory:
    """"cache for photo_file files metadata"""

    def __init__(self,
                 root_folder: Path = config.path_original_photos):
        self.root_folder: Path = root_folder
        self.photos: List[Photo] = []
        self.files_already_generated: list[str] = []

        self.photo_factory = PhotoFactoryLocalFiles()

    def refresh_directory(self):
        """
        refreshing photo_file files metadata
        """
        logger.info('Re-reading photos list.')
        self.photos = self.photo_factory.make_photos()

        # list of already-generated file derivatives (thumbnails & resized)
        absolute_paths_generated_thumbnails = find_jpg_files(config.path_generated_thumbnails)
        self.files_already_generated = [a.name for a in absolute_paths_generated_thumbnails]

        self._generate_images()
        return self

    # def _read_latest_image_dates(self, photos: list[Photo]) -> None:
    #     """
    #     called when refreshing photo_file directory; reads latest photo_file date for all plants; contains
    #     only plants that have at least one photo_file
    #     """
    #     self.latest_image_dates = {}
    #     for photo in photos:
    #         for p in photo.plants:
    #             try:
    #                 if p not in self.latest_image_dates or self.latest_image_dates[p].date < photo.record_date_time:
    #                     self.latest_image_dates[p] = ImageInfo(date=photo.record_date_time,
    #                                                            path=photo.relative_path,
    #                                                            path_thumb=photo.relative_path_thumb)
    #             except TypeError:
    #                 pass

    def _generate_images(self):
        # todo move to file upload and to new 'repair function'
        """generates photo_file derivatives (resized & thumbnail) for each original photo_file file if not
        already exists; adds relative paths to these generated images to directory (i.e. to the list of dicts (one
        dict for each photo_file file))"""
        for photo in self.photos:
            photo.generate_thumbnails(self.files_already_generated)

    # def get_photo(self, absolute_path: Path) -> Optional[Photo]:
    #     """
    #     get photo_file instance by absolute path
    #     """
    #     # find (first) object in photos directory without iterating through all or creating new list
    #     return next((p for p in self.photos if p.absolute_path == absolute_path), None)

    # def remove(self, photo: Photo, db: Session) -> None:
    #     """
    #     find the directory entry for the photo_file and remove it; physical deletion of the file
    #     is handled elsewhere but flag as deleted in db here
    #     """
    #     # todo separate dao class
    #     if db:
    #         pass
    #         # todo: remove from db images table and associated tables
    #         # # entry for the image itself (legacy)  # todo remove or raise if not found
    #         # image = db.query(Image).filter(Image.id == photo_file.id).scalar()
    #         # if not image:
    #         #     # todo raise
    #         #     pass
    #         # else:
    #         #     image.deleted = True
    #         #     db.commit()  # todo commit only at the end if everything else worked
    #
    #     if photo not in self.photos:
    #         logger.error(f"Can't remove from photo_file directory cache: not found.")
    #     else:
    #         self.photos.remove(photo)
    #         logger.info(f'Removed photo_file from PhotoDirectory Cache.')

    # def get_latest_date_per_plant(self, plant_name: str) -> ImageInfo:
    #     """called by plants resource. returns latest photo_file record date for supplied plant_name"""
    #     return self.latest_image_dates.get(plant_name)

    # def get_photo_files(self, plant_name: str = None) -> List[Photo]:
    #     """
    #     return photo_file file metadata, optionally filtered by plant_name
    #     """
    #     photo_files = self.photos if not plant_name else [p for p in self.photos if plant_name in p.plants]
    #     return photo_files

    # def get_photo_files_untagged(self) -> List[Photo]:
    #     """
    #     return photo_file file metadata for photos that have no plants tagged, yet
    #     """
    #     photo_files = [p for p in self.photos if not p.plants]
    #     return photo_files


lock_photo_directory = threading.RLock()
photo_directory: Optional[PhotoDirectory] = None


def get_photo_directory(instantiate=True) -> PhotoDirectory:
    global photo_directory
    if not photo_directory and instantiate:
        photo_directory = PhotoDirectory().refresh_directory()
    return photo_directory


@dataclass
class Photo:
    id: Optional[int]
    absolute_path: Path
    filename: str
    filename_thumb: str
    relative_path_thumb: PurePath  # relative
    relative_path: PurePath  # relative
    record_date_time: datetime.datetime
    description: Optional[str] = ''
    keywords: Optional[List] = None
    plants: Optional[List] = None  # todo make it a tuple of (plant_name, id)

    def __repr__(self):
        return f'Photo: {self.relative_path.as_posix()}'

    def generate_thumbnails(self, files_already_generated: Optional[Iterable[str]] = None):
        # todo remove when not used but replaced with function
        """
        generates photo_file derivatives (resized & thumbnail) if not already exists;
        also sets attributes for relative paths to these generated images
        """
        if not files_already_generated or self.filename_thumb not in files_already_generated:
            _ = generate_thumbnail(image=self.absolute_path,
                                   size=config.size_thumbnail_image,
                                   path_thumbnail=config.path_generated_thumbnails)


class PhotoFactoryDatabase:
    """photo_file object factory reading from database"""

    def __init__(self, db: Session):
        self.db = db

    def make_photos(self):
        """factory method for all photo_file objects"""
        images = self.db.query(Image).all()
        logger.info(f"Found {len(images)} images in database.")
        photos = [self._make_photo_from_orm_image(image) for image in images]
        return photos

    @staticmethod
    def _make_photo_from_orm_image(image: Image):
        absolute_path = config.path_photos_base.parent.joinpath(image.relative_path)
        filename = absolute_path.name
        filename_thumb = get_filename_thumb(filename)
        photo = Photo(
                id=image.id,
                absolute_path=absolute_path,
                filename=filename,
                filename_thumb=filename_thumb,
                relative_path_thumb=get_relative_path_thumb(filename_thumb),
                relative_path=get_relative_path(absolute_path),
                record_date_time=image.record_date_time,
                description=image.description,
                keywords=[k.keyword for k in image.keywords],
                plants=[i.plant_name for i in image.plants])
        return photo

    def make_photo_from_absolute_path(self, absolute_path: Path):
        raise NotImplementedError


class PhotoFactoryLocalFiles:
    """photo_file object factory reading from local files and exif tags"""

    def __init__(self):
        self.metadata_access = PhotoMetadataAccessExifTags()

    def make_photos(self):
        """factory method for all photo_file objects"""

        # read all jpg files in file system
        absolute_paths = find_jpg_files(config.path_original_photos)
        logger.info(f"Scanned through originals folder. Found {len(absolute_paths)} photo_file files.")

        photos = [self.make_photo_from_absolute_path(absolute_path=absolute_path)
                  for absolute_path in absolute_paths]
        return photos

    def make_photo_from_absolute_path(self, absolute_path: Path):
        """factory method for single photo_file object"""
        image_id = None  # todo
        absolute_path = absolute_path
        filename = absolute_path.name
        filename_thumb = get_filename_thumb(filename)
        relative_path_thumb = get_relative_path_thumb(filename_thumb)
        relative_path = get_relative_path(absolute_path)
        metadata = self.metadata_access.read_photo_metadata(absolute_path=absolute_path)

        photo = Photo(
                id=image_id,
                absolute_path=absolute_path,
                filename=filename,
                filename_thumb=filename_thumb,
                relative_path_thumb=relative_path_thumb,
                relative_path=relative_path,
                record_date_time=metadata.record_date_time,
                description=metadata.description,
                keywords=metadata.keywords,
                plants=metadata.plant_names)
        return photo


class ImageInfo(NamedTuple):
    date: datetime.date
    path: PurePath
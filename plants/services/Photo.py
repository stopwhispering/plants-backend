import datetime
from dataclasses import dataclass
from pathlib import PurePath, Path
from typing import Optional, List, Iterable
import logging

from plants import config
from plants.services.photo_metadata_access import PhotoMetadataAccess, MetadataDTO
from plants.util.filename_utils import get_generated_filename
from plants.util.image_utils import generate_thumbnail

logger = logging.getLogger(__name__)


@dataclass
class Photo:
    filename: Optional[str] = None
    filename_thumb: Optional[str] = None
    absolute_path: Optional[Path] = None
    relative_path: Optional[PurePath] = None  # relative
    relative_path_thumb: Optional[PurePath] = None  # relative
    description: Optional[str] = ''
    keywords: Optional[List] = None
    plants: Optional[List] = None
    record_date_time: Optional[datetime.datetime] = None

    metadata_access: PhotoMetadataAccess = None  # todo db / factory

    def generate_thumbnails(self, files_already_generated: Optional[Iterable[str]] = None):
        """
        generates photo derivatives (resized & thumbnail) if not already exists;
        also sets attributes for relative paths to these generated images
        """
        # generate a thumbnail...
        self.filename_thumb = get_generated_filename(self.filename,
                                                     size=config.size_thumbnail_image)
        if not files_already_generated or self.filename_thumb not in files_already_generated:
            _ = generate_thumbnail(image=self.absolute_path,
                                   size=config.size_thumbnail_image,
                                   path_thumbnail=config.path_generated_thumbnails)

        self.relative_path_thumb = config.rel_path_photos_generated.joinpath(self.filename_thumb)
        # for the frontend we need to cut off the first part of the path
        rel_path_photos_original = config.rel_path_photos_original.as_posix()
        absolute_path = self.absolute_path.as_posix()
        absolute_path = absolute_path[absolute_path.find(rel_path_photos_original):]
        self.relative_path = PurePath(absolute_path)

    def read_metadata(self):
        """retrieve metadata on photo and set corresponding attribute in photo object"""
        # todo works for namedtuple?
        (self.plants, self.keywords,
         self.description, self.record_date_time) = self.metadata_access.read_photo_metadata(
                absolute_path=self.absolute_path)

    def save_metadata(self):
        """save/update photo metadata"""
        # self.metadata_access.save_photo_metadata(photo=self)
        metadata = MetadataDTO(self.plants, self.keywords, self.description, self.record_date_time)
        self.metadata_access.save_photo_metadata(metadata=metadata, absolute_path=self.absolute_path)

        # re-read the newly updated metadata
        self.read_metadata()

    def rename_tagged_plant(self, plant_name_old: str, plant_name_new: str):
        """rename a tagged plant, both in file and in images directory; preserves last modified date of photo file"""

        self.plants.remove(plant_name_old)
        self.plants.append(plant_name_new)

        self.metadata_access.rewrite_plant_assignments(absolute_path=self.absolute_path, plants=self.plants)

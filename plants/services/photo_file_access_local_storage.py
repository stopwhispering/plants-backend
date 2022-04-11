from pathlib import Path

from plants.services.Photo import Photo
from plants.services.image_info import ImageInfo
from plants.services.photo_file_access import PhotoFileAccess, logger
from plants.services.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.util.filename_utils import find_jpg_files


class PhotoFileAccessLocalStorage(PhotoFileAccess):
    """Photo File Access from local file system"""
    def __init__(self, path_original_photos: Path, path_derived_photos: Path):
        self.path_original_photos = path_original_photos
        self.path_derived_photos = path_derived_photos

    def query_photos(self) -> list[Photo]:
        """read all photo files and create a list of dicts (one dict for each file)"""
        paths = find_jpg_files(self.path_original_photos)
        logger.info(f"Scanned through originals folder. Found {len(paths)} photo files.")
        photos = [Photo(absolute_path=absolute_path,
                        filename=absolute_path.name,
                        metadata_access=PhotoMetadataAccessExifTags()  # todo db/factory/ make dependency
                        ) for absolute_path in paths]
        self._read_metadata_all_images(photos=photos)
        self._read_latest_image_dates(photos=photos)
        return photos

    def get_generated_files(self) -> list[str]:
        """returns a list of already-generated file derivatives (thumbnails & resized)"""
        paths = find_jpg_files(self.path_derived_photos)
        return [path_full.name for path_full in paths]

    @staticmethod
    def _read_metadata_all_images(photos: list[Photo]) -> None:
        """reads metadata for each original file and parses information from it (plants list etc.), adds these
        information to directory (i.e. to the list of dicts (one dict for each photo file))"""
        logger.info(f"Starting to read metadata of {len(photos)} files")
        for photo in photos:
            photo.read_metadata()  # todo this is ugly, move sometwher else

    def _read_latest_image_dates(self, photos: list[Photo]) -> None:
        """
        called when refreshing photo directory; reads latest photo date for all plants; contains
        only plants that have at least one photo
        """
        self.latest_image_dates = {}
        for photo in photos:
            for p in photo.plants:
                try:
                    if p not in self.latest_image_dates or self.latest_image_dates[p].date < photo.record_date_time:
                        self.latest_image_dates[p] = ImageInfo(date=photo.record_date_time,
                                                               path=photo.relative_path,
                                                               path_thumb=photo.relative_path_thumb)
                except TypeError:
                    pass
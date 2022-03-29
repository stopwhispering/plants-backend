import datetime
from dataclasses import dataclass
from pathlib import PurePath, Path
from typing import Optional, List, Iterable
import piexif
import logging
from piexif import InvalidImageDataError

from plants import config
from plants.util.exif_utils import auto_rotate_jpeg, decode_keywords_tag, decode_record_date_time, \
    set_modified_date, encode_record_date_time, modified_date, encode_keywords_tag, exif_dict_has_all_relevant_tags
from plants.util.filename_utils import get_generated_filename
from plants.util.image_utils import generate_thumbnail

logger = logging.getLogger(__name__)


@dataclass
class Photo:
    filename_thumb: Optional[str] = None
    path_thumb: Optional[PurePath] = None  # relative
    path_original: Optional[PurePath] = None  # relative
    path_full_local: Optional[Path] = None
    filename: Optional[str] = None
    tag_description: Optional[str] = ''
    tag_keywords: Optional[List] = None
    tag_authors_plants: Optional[List] = None
    record_date_time: Optional[datetime.datetime] = None

    def parse_exif_tags(self):
        """
        (re-)reads exif info from file in attribute path_full_local and parses information from it (plants list,
        keywords, description, etc.
        """
        if not self.path_full_local:
            raise ValueError('File path not set.')

        try:
            exif_dict = piexif.load(self.path_full_local.as_posix())
        except InvalidImageDataError:
            logger.warning(f'Invalid Image Type Error occured when reading EXIF Tags for {self.path_full_local}.')
            self.tag_description = ''
            self.tag_keywords = []
            self.tag_authors_plants = []
            self.record_date_time = None
            return
        except ValueError:
            # todo not a true jpeg or similar
            a = 1

        auto_rotate_jpeg(self.path_full_local, exif_dict)

        try:  # description
            self.tag_description = exif_dict['0th'][270].decode('utf-8')  # windows description/title tag
        except KeyError:
            self.tag_description = ''

        try:  # keywords
            self.tag_keywords = decode_keywords_tag(exif_dict['0th'][40094])  # Windows Keywords Tag
            if not self.tag_keywords[0]:  # ''
                self.tag_keywords = []
        except KeyError:
            self.tag_keywords = []

        try:  # plants (list); read from authors exif tag
            # if 315 in exif_dict['0th']:
            self.tag_authors_plants = exif_dict['0th'][315].decode('utf-8').split(';')  # Windows Authors Tag
            if not self.tag_authors_plants[0]:  # ''
                self.tag_authors_plants = []
        except KeyError:
            self.tag_authors_plants = []

        try:  # record date+time
            self.record_date_time = decode_record_date_time(exif_dict["Exif"][36867])
        except KeyError:
            self.record_date_time = None

    def generate_thumbnails(self, files_already_generated: Optional[Iterable[str]] = None):
        """
        generates image derivatives (resized & thumbnail) if not already exists;
        also sets attributes for relative paths to these generated images
        """
        # generate a thumbnail...
        self.filename_thumb = get_generated_filename(self.filename,
                                                     size=config.size_thumbnail_image)
        if not files_already_generated or self.filename_thumb not in files_already_generated:
            _ = generate_thumbnail(image=self.path_full_local,
                                   size=config.size_thumbnail_image,
                                   path_thumbnail=config.path_generated_thumbnails)

        self.path_thumb = config.rel_path_photos_generated.joinpath(self.filename_thumb)
        # for the frontend we need to cut off the first part of the path
        rel_path_photos_original = config.rel_path_photos_original.as_posix()
        path_full_local = self.path_full_local.as_posix()
        path_original = path_full_local[path_full_local.find(rel_path_photos_original):]
        self.path_original = PurePath(path_original)

    def write_exif_tags(self) -> None:
        """
        adjust exif tags in file described in photo object; optionally append to photo directory (used for newly
        uploaded photo files)
        """
        tag_descriptions = self.tag_description.encode('utf-8')
        tag_keywords = encode_keywords_tag(self.tag_keywords)

        if self.tag_authors_plants:
            tag_authors_plants = ';'.join(self.tag_authors_plants).encode('utf-8')
        else:
            tag_authors_plants = b''

        exif_dict = piexif.load(self.path_full_local.as_posix())

        # check if any of the tags has been changed or if any of the relevant tags is missing altogether
        if (not exif_dict_has_all_relevant_tags(exif_dict)
                or exif_dict['0th'][270] != tag_descriptions
                or exif_dict['0th'][40094] != tag_keywords
                or exif_dict['0th'][315] != tag_authors_plants):

            exif_dict['0th'][270] = tag_descriptions  # windows description/title tag
            exif_dict['0th'][40094] = tag_keywords  # Windows Keywords Tag
            exif_dict['0th'][315] = tag_authors_plants  # Windows Authors Tag

            # we want to preserve the file's last-change-date
            # additionally, if image does not have a record time in exif tag,
            #    then we enter the last-changed-date there
            modified_time_seconds = modified_date(self.path_full_local)  # seconds
            if not exif_dict['Exif'].get(36867):
                dt = datetime.datetime.fromtimestamp(modified_time_seconds)
                b_dt = encode_record_date_time(dt)
                exif_dict['Exif'][36867] = b_dt

            # fix some problem with windows photo editor writing exif tag in wrong format
            if exif_dict.get('GPS') and type(exif_dict['GPS'].get(11)) is bytes:
                del exif_dict['GPS'][11]
            try:
                exif_bytes = piexif.dump(exif_dict)
            except ValueError as e:
                logger.warning(f'Catched exception when modifying exif: {str(e)}. Trying again after deleting '
                               'embedded thumbnail.')
                del exif_dict['thumbnail']
                exif_bytes = piexif.dump(exif_dict)

            # ... save using piexif
            piexif.insert(exif_bytes, self.path_full_local.as_posix())
            # reset modified time
            set_modified_date(self.path_full_local, modified_time_seconds)  # set access and modifide date

            # re-read the newly updated exif tags
            self.parse_exif_tags()

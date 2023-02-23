import datetime
import logging
from dataclasses import dataclass
from pathlib import Path

import piexif
from piexif import InvalidImageDataError

from plants import local_config
from plants.modules.image.exif_utils import (
    auto_rotate_jpeg,
    decode_keywords_tag,
    decode_record_date_time,
    encode_keywords_tag,
    encode_record_date_time,
    exif_dict_has_all_relevant_tags,
    modified_date,
    set_modified_date,
)

logger = logging.getLogger(__name__)


@dataclass
class MetadataDTO:
    plant_names: list[str]
    keywords: list[str]
    description: str
    record_date_time: datetime.datetime | None = None


class PhotoMetadataAccessExifTags:
    """Access to Photo Metadata via jpeg exif tags."""

    def read_photo_metadata(self, absolute_path: Path) -> MetadataDTO:
        """Retrieve metadata on photo_file from jpeg file exif tags."""
        return self._parse_exif_tags(absolute_path=absolute_path)

    async def save_photo_metadata(
        self,
        image_absolute_path: Path,
        # image_id: int,
        plant_names: list[str],
        keywords: list[str],
        description: str,
        # image_dal: ImageDAL,
    ) -> None:
        """Save/update photo_file metadata."""
        # get file system path to the image
        # image = await image_dal.by_id(image_id)

        metadata = MetadataDTO(
            plant_names=plant_names,
            keywords=keywords,
            description=description,
        )
        self._write_exif_tags(metadata=metadata, absolute_path=image_absolute_path)
        # absolute_path=image.absolute_path)

    def rewrite_plant_assignments(self, absolute_path: Path, plants: list[str]) -> None:
        """Rewrite the plants assigned to the photo_file at the supplied path."""
        self._rewrite_plant_assignments_in_exif_tags(
            absolute_path=absolute_path, plants=plants
        )

    @staticmethod
    def _parse_exif_tags(absolute_path: Path) -> MetadataDTO:
        """Reads exif info from file in attribute absolute_path and parses information
        from it (plants list, keywords, description, etc."""
        if not absolute_path:
            raise ValueError("File path not set.")

        try:
            exif_dict = piexif.load(absolute_path.as_posix())
        except InvalidImageDataError:
            logger.warning(
                f"Invalid Image Type Error occured when reading EXIF Tags "
                f"for {absolute_path}."
            )
            description = ""
            keywords = []
            plants = []
            record_date_time = None
            return MetadataDTO(
                plant_names=plants,
                keywords=keywords,
                description=description,
                record_date_time=record_date_time,
            )

        auto_rotate_jpeg(absolute_path, exif_dict)  # todo move elsewhere

        try:  # description
            description = exif_dict["0th"][270].decode(
                "utf-8"
            )  # windows description/title tag
        except KeyError:
            description = ""

        try:  # keywords
            keywords = decode_keywords_tag(
                exif_dict["0th"][40094]
            )  # Windows Keywords Tag
            if not keywords[0]:  # ''
                keywords = []
        except KeyError:
            keywords = []

        try:  # plants (list); read from authors exif tag
            # if 315 in exif_dict['0th']:
            plants = (
                exif_dict["0th"][315].decode("utf-8").split(";")
            )  # Windows Authors Tag
            if not plants[0]:  # ''
                plants = []
        except KeyError:
            plants = []

        try:  # record date+time
            record_date_time = decode_record_date_time(exif_dict["Exif"][36867])
        except KeyError:
            record_date_time = None

        return MetadataDTO(
            plant_names=plants,
            keywords=keywords,
            description=description,
            record_date_time=record_date_time,
        )

    @staticmethod
    def _write_exif_tags(absolute_path: Path, metadata: MetadataDTO) -> None:
        """Adjust exif tags in file described in photo_file object; optionally append to
        photo_file directory (used for newly uploaded photo_file files)."""
        tag_descriptions = metadata.description.encode("utf-8")
        tag_keywords = encode_keywords_tag(metadata.keywords)

        if metadata.plant_names:
            tag_authors_plants = ";".join(metadata.plant_names).encode("utf-8")
        else:
            tag_authors_plants = b""

        if not absolute_path.is_file():
            if local_config.log_settings.ignore_missing_image_files:
                logger.warning(
                    f"File {absolute_path} not found. Can"
                    "t write EXIF Tags. Ignoring."
                )
                return
            else:
                raise FileNotFoundError(f"File {absolute_path} not found.")

        exif_dict = piexif.load(absolute_path.as_posix())

        # check if any of the tags has been changed or if any of the relevant
        # tags is missing altogether
        if (
            not exif_dict_has_all_relevant_tags(exif_dict)
            or exif_dict["0th"][270] != tag_descriptions
            or exif_dict["0th"][40094] != tag_keywords
            or exif_dict["0th"][315] != tag_authors_plants
        ):
            exif_dict["0th"][270] = tag_descriptions  # windows description/title tag
            exif_dict["0th"][40094] = tag_keywords  # Windows Keywords Tag
            exif_dict["0th"][315] = tag_authors_plants  # Windows Authors Tag

            # we want to preserve the file's last-change-date
            # additionally, if photo_file does not have a record time in exif tag,
            #    then we enter the last-changed-date there
            modified_time_seconds = modified_date(absolute_path)  # seconds
            if not exif_dict["Exif"].get(36867):
                dt = datetime.datetime.fromtimestamp(modified_time_seconds)
                b_dt = encode_record_date_time(dt)
                exif_dict["Exif"][36867] = b_dt

            # fix some problem with windows photo_file editor writing exif tag in
            # wrong format
            if exif_dict.get("GPS") and type(exif_dict["GPS"].get(11)) is bytes:
                del exif_dict["GPS"][11]
            try:
                exif_bytes = piexif.dump(exif_dict)
            except ValueError as e:
                logger.warning(
                    f"Catched exception when modifying exif: {str(e)}. Trying again "
                    "after deleting embedded thumbnail."
                )
                del exif_dict["thumbnail"]
                exif_bytes = piexif.dump(exif_dict)

            # ... save using piexif
            piexif.insert(exif_bytes, absolute_path.as_posix())
            # reset modified time
            set_modified_date(
                absolute_path, modified_time_seconds
            )  # set access and modifide date

    @staticmethod
    def _rewrite_plant_assignments_in_exif_tags(absolute_path: Path, plants: list[str]):
        """rewrite the plants assigned to the photo_file at the supplied path; keep the
        last-modifide date (called in context of renaming)"""
        if (
            not absolute_path.is_file()
            and local_config.log_settings.ignore_missing_image_files
        ):
            return

        # we want to preserve the file's last-change-date
        modified_time_seconds = modified_date(absolute_path)  # seconds

        # get a new list of plants for the photo_file and convert it to exif tag syntax
        tag_authors_plants = ";".join(plants).encode("utf-8")

        # load file's current exif tags and overwrite the authors tag used for
        # saving plants
        exif_dict = piexif.load(absolute_path.as_posix())
        exif_dict["0th"][315] = tag_authors_plants  # Windows Authors Tag

        # update the file's exif tags physically
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, absolute_path.as_posix())

        # reset file's last modified date to the previous date
        set_modified_date(
            absolute_path, modified_time_seconds
        )  # set access and modified date

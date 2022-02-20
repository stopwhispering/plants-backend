import piexif
import logging

from plants.util.exif_utils import modified_date, set_modified_date
from plants.services.Photo import Photo

logger = logging.getLogger(__name__)


def rename_plant_in_exif_tags(image: Photo, plant_name_old: str, plant_name_new: str) -> None:
    """
    renames plant in image's plant tags; both in files and in images directory; preserves
    last modified date of image file
    """
    # we want to preserve the file's last-change-date
    modified_time_seconds = modified_date(image.path_full_local)  # seconds

    # get a new list of plants for the image and convert it to exif tag syntax
    image.tag_authors_plants.remove(plant_name_old)
    image.tag_authors_plants.append(plant_name_new)
    tag_authors_plants = ';'.join(image.tag_authors_plants).encode('utf-8')

    # load file's current exif tags and overwrite the authors tag used for saving plants
    exif_dict = piexif.load(image.path_full_local.as_posix())
    exif_dict['0th'][315] = tag_authors_plants  # Windows Authors Tag

    # update the file's exif tags physically
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, image.path_full_local.as_posix())

    # reset file's last modified date to the previous date
    set_modified_date(image.path_full_local, modified_time_seconds)  # set access and modifide date

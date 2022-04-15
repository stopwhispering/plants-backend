from typing import List
import logging

import aiofiles
from fastapi import UploadFile
from sqlalchemy.orm import Session

from plants import config
from plants.models.image_models import Image, create_image
from plants.models.plant_models import Plant
from plants.constants import RESIZE_SUFFIX

from plants.services.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.simple_services.image_services import resizing_required, get_relative_path
from plants.util.exif_utils import read_record_datetime_from_exif_tags
from plants.util.filename_utils import with_suffix
from plants.util.image_utils import resize_image, generate_thumbnail

logger = logging.getLogger(__name__)


# def get_distinct_keywords_from_image_files() -> Set[str]:
#     """
#     get set of all keywords from all the images in the directory
#     """
#     with lock_photo_directory:
#         photo_directory = get_photo_directory()
#
#         # get flattening generator and create set of distinct keywords
#         keywords_nested_gen = (photo.keywords for photo in photo_directory.photos if photo.keywords)
#         return set(chain.from_iterable(keywords_nested_gen))


# def _get_photos_by_plant_name(plant_name: str) -> Generator[Photo, None, None]:
#     """
#     returns generator of photo_file entries from photo_file directory tagging supplied plant name
#     """
#     with lock_photo_directory:
#         photo_directory = get_photo_directory()
#         return (p for p in photo_directory.photos if plant_name in p.plants)
#     # isinstance(p.plants, list) and plant_name in p.plants]



def rename_plant_in_image_files(plant: Plant, plant_name_old: str) -> int:
    """
    in each photo_file file that has the old plant name tagged, fit tag to the new plant name
    """
    if not plant.images:
        logger.info(f'No photo_file tag to change for {plant_name_old}.')
    for image in plant.images:
        plant_names = [p.plant_name for p in image.plants]
        PhotoMetadataAccessExifTags().rewrite_plant_assignments(absolute_path=image.absolute_path,
                                                                plants=plant_names)

    # # get the relevant images from the photo_file directory cache
    # photos = _get_photos_by_plant_name(plant_name_old)
    # count_modified = 0
    # if not photos:
    #     logger.info(f'No photo_file tag to change for {plant_name_old}.')
    #
    # photo: Photo
    # for photo in photos:
    #     # double check
    #     if plant_name_old in photo.plants:
    #         logger.info(f"Switching plant_names tag in jpg image exif tags: {photo.absolute_path}")
    #         photo.rename_tagged_plant(plant_name_old=plant_name_old, plant_name_new=plant.plant_name)
    #
    #         PhotoMetadataAccessExifTags().rewrite_plant_assignments(absolute_path=photo.absolute_path,
    #                                                                 plants=photo.plants)
    #
    #         count_modified += 1

    # note: there's no need to upload the cache as we did modify directly in the cache above
    return len(plant.images)


async def save_image_files(files: List[UploadFile],
                           db: Session,
                           plant_ids: tuple[int] = (),
                           keywords: tuple[str] = ()
                           ) -> list[Image]:
    """save the files supplied as starlette uploadfiles on os; assign plants and keywords"""
    images = []
    for photo_upload in files:
        # save to file system
        path = config.path_original_photos_uploaded.joinpath(photo_upload.filename)
        logger.info(f'Saving {path}.')

        async with aiofiles.open(path, 'wb') as out_file:
            content = await photo_upload.read()  # async read
            await out_file.write(content)  # async write

        # photo_upload.save(path)  # we can't use object first and then save as this alters file object

        # resize file by lowering resolution if required
        if not config.resizing_size:
            pass
        elif not resizing_required(path, config.resizing_size):
            logger.info(f'No resizing required.')
        else:
            logger.info(f'Saving and resizing {path}.')
            resize_image(path=path,
                         save_to_path=with_suffix(path, RESIZE_SUFFIX),
                         size=config.resizing_size,
                         quality=config.jpg_quality)
            path = with_suffix(path, RESIZE_SUFFIX)

        # add to db
        record_datetime = read_record_datetime_from_exif_tags(absolute_path=path)
        plants = [Plant.get_plant_by_plant_id(plant_id=p, db=db, raise_exception=True) for p in plant_ids]
        image: Image = create_image(db=db,
                                    relative_path=get_relative_path(path),
                                    record_date_time=record_datetime,
                                    keywords=keywords,
                                    plants=plants)

        # generate thumbnail photo_file for frontend display and update file's metadata
        # photo.generate_thumbnails()
        generate_thumbnail(image=path,
                           size=config.size_thumbnail_image,
                           path_thumbnail=config.path_generated_thumbnails)

        # save metadata in jpg exif tags
        PhotoMetadataAccessExifTags().save_photo_metadata(absolute_path=path,
                                                          plant_names=[p.plant_name for p in plants],
                                                          keywords=list(keywords),
                                                          description='')
        images.append(image)

    return images
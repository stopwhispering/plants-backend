from typing import List
import logging
import os

import aiofiles
from fastapi import UploadFile
from sqlalchemy.orm import Session

from plants import config
from plants.models.image_models import Image, create_image
from plants.models.plant_models import Plant
from plants.constants import RESIZE_SUFFIX

from plants.services.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.services.image_services_simple import resizing_required, get_relative_path
from plants.util.exif_utils import read_record_datetime_from_exif_tags
from plants.util.filename_utils import with_suffix
from plants.util.image_utils import resize_image, generate_thumbnail
from plants.util.ui_utils import throw_exception

logger = logging.getLogger(__name__)


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


def delete_image_file_and_db_entries(image: Image, db: Session):
    """delete image file and entries in db"""
    if image.image_to_event_associations:
        logger.info(f'Deleting {len(image.image_to_event_associations)} associated Image to Event associations.')
        [db.delete(a) for a in image.image_to_event_associations]
        image.events = []
    if image.image_to_plant_associations:
        logger.info(f'Deleting {len(image.image_to_plant_associations)} associated Image to Plant associations.')
        [db.delete(a) for a in image.image_to_plant_associations]
        image.plants = []
    if image.image_to_taxon_associations:
        logger.info(f'Deleting {len(image.image_to_taxon_associations)} associated Image to Taxon associations.')
        [db.delete(a) for a in image.image_to_taxon_associations]
        image.taxa = []
    if image.keywords:
        logger.info(f'Deleting {len(image.keywords)} associated Keywords.')
        [db.delete(k) for k in image.keywords]
    db.delete(image)
    # we're committing at the end if deletion works; in case of a problem, flushing will raise exception
    # in most situations, too
    db.flush()

    old_path = image.absolute_path
    if not old_path.is_file():
        logger.error(err_msg := f"File selected to be deleted not found: {old_path}")
        throw_exception(err_msg)

    new_path = config.path_deleted_photos.joinpath(old_path.name)
    try:
        os.replace(src=old_path,
                   dst=new_path)  # silently overwrites if privileges are sufficient
    except OSError as e:
        logger.error(err_msg := f'OSError when moving file {old_path} to {new_path}', exc_info=e)
        throw_exception(err_msg, description=f'Filename: {old_path.name}')
    logger.info(f'Moved file {old_path} to {new_path}')

    db.commit()
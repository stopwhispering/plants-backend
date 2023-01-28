from pathlib import Path
from typing import List
import logging
import os

import aiofiles
from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from plants import local_config, settings, constants
from plants.modules.image.models import Image, create_image, ImageToPlantAssociation, ImageToEventAssociation, \
    ImageToTaxonAssociation, ImageKeyword
from plants.modules.image.schemas import FBImage, FBImagePlantTag
from plants.modules.plant.models import Plant
from plants.modules.taxon.models import TaxonOccurrenceImage

from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.image.image_services_simple import resizing_required, get_relative_path
from plants.modules.image.exif_utils import read_record_datetime_from_exif_tags
from plants.modules.image.util import resize_image, generate_thumbnail, get_thumbnail_name
from plants.shared.path_utils import with_suffix, get_generated_filename
from plants.shared.message__services import throw_exception

logger = logging.getLogger(__name__)

NOT_AVAILABLE_IMAGE_FILENAME = "not_available.png"


def rename_plant_in_image_files(plant: Plant, plant_name_old: str) -> int:
    """
    in each photo_file file that has the old plant name tagged, fit tag to the new plant name
    """
    if not plant.images:
        logger.info(f'No photo_file tag to change for {plant_name_old}.')
    for image in plant.images:
        image: Image
        plant_names = [p.plant_name for p in image.plants]
        PhotoMetadataAccessExifTags().rewrite_plant_assignments(absolute_path=image.absolute_path,
                                                                plants=plant_names)

    # note: there's no need to upload the cache as we did modify directly in the cache above
    return len(plant.images)


async def save_image_files(files: List[UploadFile],
                           db: Session,
                           plant_ids: tuple[int] = (),
                           keywords: tuple[str] = ()
                           ) -> list[FBImage]:
    """save the files supplied as starlette uploadfiles on os; assign plants and keywords"""
    images = []
    for photo_upload in files:
        # save to file system
        path = settings.paths.path_original_photos_uploaded.joinpath(photo_upload.filename)
        logger.info(f'Saving {path}.')

        async with aiofiles.open(path, 'wb') as out_file:
            content = await photo_upload.read()  # async read
            await out_file.write(content)  # async write

        # photo_upload.save(path)  # we can't use object first and then save as this alters file object

        # resize file by lowering resolution if required
        if not settings.images.resizing_size:
            pass
        elif not resizing_required(path, settings.images.resizing_size):
            logger.info(f'No resizing required.')
        else:
            logger.info(f'Saving and resizing {path}.')
            resize_image(path=path,
                         save_to_path=with_suffix(path, constants.RESIZE_SUFFIX),
                         size=settings.images.resizing_size,
                         quality=settings.images.jpg_quality)
            path = with_suffix(path, constants.RESIZE_SUFFIX)

        # add to db
        record_datetime = read_record_datetime_from_exif_tags(absolute_path=path)
        plants = [Plant.get_plant_by_plant_id(plant_id=p, db=db, raise_exception=True) for p in plant_ids]
        image: Image = create_image(db=db,
                                    relative_path=get_relative_path(path),
                                    record_date_time=record_datetime,
                                    keywords=keywords,
                                    plants=plants)

        # generate thumbnails for frontend display
        for size in settings.images.sizes:
            generate_thumbnail(image=path,
                               size=size,
                               path_thumbnail=settings.paths.path_generated_thumbnails,
                               ignore_missing_image_files=local_config.ignore_missing_image_files)

        # save metadata in jpg exif tags
        PhotoMetadataAccessExifTags().save_photo_metadata(image_id=image.id,
                                                          plant_names=[p.plant_name for p in plants],
                                                          keywords=list(keywords),
                                                          description='',
                                                          db=db)
        images.append(image)

    db.commit()
    return [_to_response_image(i) for i in images]


def delete_image_file_and_db_entries(image: Image, db: Session):
    """delete image file and entries in db"""
    ai: ImageToEventAssociation
    ap: ImageToPlantAssociation
    at: ImageToTaxonAssociation
    if image.image_to_event_associations:
        logger.info(f'Deleting {len(image.image_to_event_associations)} associated Image to Event associations.')
        [db.delete(ai) for ai in image.image_to_event_associations]
        image.events = []
    if image.image_to_plant_associations:
        logger.info(f'Deleting {len(image.image_to_plant_associations)} associated Image to Plant associations.')
        [db.delete(ap) for ap in image.image_to_plant_associations]
        image.plants = []
    if image.image_to_taxon_associations:
        logger.info(f'Deleting {len(image.image_to_taxon_associations)} associated Image to Taxon associations.')
        [db.delete(at) for at in image.image_to_taxon_associations]
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
        if local_config.ignore_missing_image_files:
            logger.warning(f'Image file {old_path} to be deleted not found.')
            return
        else:
            logger.error(err_msg := f"File selected to be deleted not found: {old_path}")
            throw_exception(err_msg)

    new_path = settings.paths.path_deleted_photos.joinpath(old_path.name)
    try:
        os.replace(src=old_path,
                   dst=new_path)  # silently overwrites if privileges are sufficient
    except OSError as e:
        logger.error(err_msg := f'OSError when moving file {old_path} to {new_path}', exc_info=e)
        throw_exception(err_msg, description=f'Filename: {old_path.name}')
    logger.info(f'Moved file {old_path} to {new_path}')


# def _get_sized_image_path(filename: str, size_px: int) -> Path:
#     """return the path to the image file with the given pixel size"""
#

def get_image_path_by_size(filename: str, db: Session, width: int | None, height: int | None) -> Path:
    if (width is None or height is None) and not (width is None and height is None):
        logger.error(err_msg := f'Either supply width and height or neither of them.')
        throw_exception(err_msg)

    if width is None:
        # get image db entry for the directory it is stored at in local filesystem
        image: Image = Image.get_image_by_filename(db=db, filename=filename)
        return Path(image.absolute_path)

    else:
        # the pixel size is part of the resized images' filenames rem size must be converted to px
        filename_sized = get_generated_filename(filename, (width, height))
        # return get_absolute_path_for_generated_image(filename_sized, settings.paths.path_generated_thumbnails)
        return settings.paths.path_generated_thumbnails.joinpath(filename)


def get_dummy_image_path_by_size(width: int | None, height: int | None) -> Path:
    if width:
        size = (width, height)
        filename = get_generated_filename(NOT_AVAILABLE_IMAGE_FILENAME, size)
    else:
        filename = NOT_AVAILABLE_IMAGE_FILENAME
    path = Path("./static/").joinpath(filename)
    if not path.is_file():
        logger.error(err_msg := f'Dummy image file not found: {path}')
        throw_exception(err_msg)
    return path


def read_image_by_size(filename: str, db: Session, width: int | None, height: int | None) -> bytes:
    """return the image in specified size as bytes"""
    path = get_image_path_by_size(filename=filename,
                                  db=db,
                                  width=width,
                                  height=height)

    if not path.is_file():
        # return default image on dev environment where most photos are missing
        if local_config.ignore_missing_image_files:
            path = get_dummy_image_path_by_size(width=width, height=height)
        else:
            logger.error(err_msg := f'Image file not found: {path}')
            throw_exception(err_msg)

    with open(path, "rb") as image:
        image_bytes: bytes = image.read()

    return image_bytes


def read_occurrence_thumbnail(gbif_id: int, occurrence_id: int, img_no: int, db: Session):
    taxon_occurrence_image: TaxonOccurrenceImage = (db.query(TaxonOccurrenceImage).filter(
                                    TaxonOccurrenceImage.gbif_id == gbif_id,
                                    TaxonOccurrenceImage.occurrence_id == occurrence_id,
                                    TaxonOccurrenceImage.img_no == img_no).first())
    if not taxon_occurrence_image:
        logger.error(err_msg := f'Occurrence thumbnail file not found: {gbif_id}/{occurrence_id}/{img_no}')
        throw_exception(err_msg)

    path = settings.paths.path_generated_thumbnails_taxon.joinpath(taxon_occurrence_image.filename_thumbnail)
    if not path.is_file():
        # return default image on dev environment where most photos are missing
        if local_config.ignore_missing_image_files:
            path = get_dummy_image_path_by_size(width=settings.images.size_thumbnail_image_taxon[0],
                                                height=settings.images.size_thumbnail_image_taxon[1])
        else:
            logger.error(err_msg := f'Occurence thumbnail file not found: {path}')
            throw_exception(err_msg)

    with open(path, "rb") as image:
        image_bytes: bytes = image.read()

    return image_bytes


def _generate_missing_thumbnails(images: list[Image]):
    count_already_existed = 0
    count_generated = 0
    count_files_not_found = 0
    for i, image in enumerate(images):

        if not image.absolute_path.is_file():
            count_files_not_found += 1
            logger.error(f"File not found: {image.absolute_path}")
            continue

        image: Image
        for size in settings.images.sizes:
            path_thumbnail = settings.paths.path_generated_thumbnails.joinpath(get_thumbnail_name(image.filename, size))
            if path_thumbnail.is_file():
                count_already_existed += 1
            else:
                generate_thumbnail(image=image.absolute_path,
                                   size=size,
                                   path_thumbnail=settings.paths.path_generated_thumbnails,
                                   ignore_missing_image_files=local_config.ignore_missing_image_files)
                count_generated += 1
                logger.info(f'Generated thumbnail in size {size} for {image.absolute_path}')

    logger.info(f'Thumbnail Generation - Count already existed: {count_already_existed}')
    logger.info(f'Thumbnail Generation - Count generated: {count_generated}')
    logger.info(f'Thumbnail Generation - Files not found: {count_files_not_found}')


def trigger_generation_of_missing_thumbnails(db: Session, background_tasks: BackgroundTasks) -> str:
    images: list[Image] = db.query(Image).all()
    logger.info(msg := f"Generating thumbnails for {len(images)} images in "
                       f"sizes: {settings.images.sizes} in background.")
    background_tasks.add_task(_generate_missing_thumbnails, images)
    return msg


def fetch_images_for_plant(plant_id: int, db: Session) -> list[FBImage]:
    plant = Plant.get_plant_by_plant_id(plant_id, db=db, raise_exception=True)
    images = [_to_response_image(image) for image in plant.images]
    return images


def _to_response_image(image: Image) -> FBImage:
    k: ImageKeyword
    return FBImage(
        id=image.id,
        filename=image.filename or '',
        keywords=[{'keyword': k.keyword} for k in image.keywords],
        plants=[FBImagePlantTag(
            plant_id=p.id,
            plant_name=p.plant_name,
            plant_name_short=_shorten_plant_name(p.plant_name),
            # key=p.plant_name,
            # text=p.plant_name,
        ) for p in image.plants],
        description=image.description,
        record_date_time=image.record_date_time)


def fetch_untagged_images(db: Session) -> list[FBImage]:
    untagged_images = db.query(Image).filter(~Image.plants.any()).all()  # noqa
    return [_to_response_image(image) for image in untagged_images]


def _shorten_plant_name(plant_name: str) -> str:
    """shorten plant name to 20 chars for display in ui5 table"""
    return (plant_name[:settings.frontend.restrictions.length_shortened_plant_name_for_tag - 3] + '...'
            if len(plant_name) > settings.frontend.restrictions.length_shortened_plant_name_for_tag
            else plant_name)


def get_distinct_image_keywords(db: Session) -> set[str]:
    """
    get set of all image keywords
    """
    keyword_tuples = db.query(ImageKeyword.keyword).distinct().all()
    return {k[0] for k in keyword_tuples}
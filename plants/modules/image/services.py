from pathlib import Path, PurePath
from typing import List, Sequence
import logging
import os
from datetime import datetime

import aiofiles
from fastapi import UploadFile, BackgroundTasks
from starlette.concurrency import run_in_threadpool

from plants import local_config, settings, constants
from plants.modules.image.models import Image, ImageToPlantAssociation, ImageToEventAssociation, \
    ImageToTaxonAssociation, ImageKeyword
from plants.modules.image.schemas import ImageCreateUpdate, FBImagePlantTag
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.modules.taxon.models import TaxonOccurrenceImage

from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.image.image_services_simple import resizing_required, get_relative_path
from plants.modules.image.exif_utils import read_record_datetime_from_exif_tags
from plants.modules.image.util import resize_image, generate_thumbnail, get_thumbnail_name
from plants.shared.path_utils import with_suffix, get_generated_filename
from plants.shared.message_services import throw_exception

logger = logging.getLogger(__name__)

NOT_AVAILABLE_IMAGE_FILENAME = "not_available.png"


def _rename_plant_in_image_files(images: list[Image], exif: PhotoMetadataAccessExifTags):
    for image in images:
        plant_names = [p.plant_name for p in image.plants]
        exif.rewrite_plant_assignments(absolute_path=image.absolute_path, plants=plant_names)


async def rename_plant_in_image_files(plant: Plant, plant_name_old: str, image_dal: ImageDAL) -> int:
    """
    in each photo_file file that has the old plant name tagged, fit tag to the new plant name
    """
    if not plant.images:
        logger.info(f'No photo_file tag to change for {plant_name_old}.')
    exif = PhotoMetadataAccessExifTags()
    # reload images to include their relationships (lazy loading not allowed in async mode)
    images = await image_dal.by_ids([i.id for i in plant.images])
    await run_in_threadpool(_rename_plant_in_image_files, images=images, exif=exif)


    #
    # await run_in_threadpool(exif.rewrite_plant_assignments,
    #                         absolute_path=image.absolute_path,
    #                         plants=plant_names)
    # for image in images:
    #     # reload image including it's relationships (lazy loading not allowed in async mode)
    #     _rename_plant_in_image_files(image, exif)
    #     # await run_in_threadpool(exif.rewrite_plant_assignments,
    #     #                         absolute_path=image.absolute_path,
    #     #                         plants=plant_names)
    #     # PhotoMetadataAccessExifTags().rewrite_plant_assignments(absolute_path=image.absolute_path,
    #     #                                                         plants=plant_names)

    # note: there's no need to upload the cache as we did modify directly in the cache above
    return len(images)


async def save_image_files(files: List[UploadFile],
                           image_dal: ImageDAL,
                           plant_dal: PlantDAL,
                           plant_ids: tuple[int] = (),
                           keywords: tuple[str] = ()
                           ) -> list[ImageCreateUpdate]:
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
        plants = [await plant_dal.by_id(p) for p in plant_ids]
        image: Image = await _create_image(image_dal=image_dal,
                                           relative_path=get_relative_path(path),
                                           record_date_time=record_datetime,
                                           keywords=keywords,
                                           plants=plants)

        # generate thumbnails for frontend display
        for size in settings.images.sizes:
            generate_thumbnail(image=path,
                               size=size,
                               path_thumbnail=settings.paths.path_generated_thumbnails,
                               ignore_missing_image_files=local_config.log_settings.ignore_missing_image_files)

        # save metadata in jpg exif tags
        await PhotoMetadataAccessExifTags().save_photo_metadata(image_id=image.id,
                                                                plant_names=[p.plant_name for p in plants],
                                                                keywords=list(keywords),
                                                                description='',
                                                                image_dal=image_dal)
        images.append(image)

    return [_to_response_image(i) for i in images]


async def delete_image_file_and_db_entries(image: Image, image_dal: ImageDAL):
    """delete image file and entries in db"""
    ai: ImageToEventAssociation
    ap: ImageToPlantAssociation
    at: ImageToTaxonAssociation
    if image.image_to_event_associations:
        logger.info(f'Deleting {len(image.image_to_event_associations)} associated Image to Event associations.')
        await image_dal.delete_image_to_event_associations(image, image.image_to_event_associations)
        image.events = []
    if image.image_to_plant_associations:
        logger.info(f'Deleting {len(image.image_to_plant_associations)} associated Image to Plant associations.')
        await image_dal.delete_image_to_plant_associations(image, image.image_to_plant_associations)
        image.plants = []
    if image.image_to_taxon_associations:
        logger.info(f'Deleting {len(image.image_to_taxon_associations)} associated Image to Taxon associations.')
        await image_dal.delete_image_to_taxon_associations(image, image.image_to_taxon_associations)
        image.taxa = []
    if image.keywords:
        logger.info(f'Deleting {len(image.keywords)} associated Keywords.')
        await image_dal.delete_keywords_from_image(image, image.keywords)

    await image_dal.delete_image(image)

    old_path = image.absolute_path
    if not old_path.is_file():
        if local_config.log_settings.ignore_missing_image_files:
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

async def get_image_path_by_size(filename: str, width: int | None, height: int | None, image_dal: ImageDAL) -> Path:
    if (width is None or height is None) and not (width is None and height is None):
        logger.error(err_msg := f'Either supply width and height or neither of them.')
        throw_exception(err_msg)

    if width is None:
        # get image db entry for the directory it is stored at in local filesystem
        image: Image = await image_dal.get_image_by_filename(filename=filename)
        return Path(image.absolute_path)

    else:
        # the pixel size is part of the resized images' filenames rem size must be converted to px
        filename_sized = get_generated_filename(filename, (width, height))
        # return get_absolute_path_for_generated_image(filename_sized, settings.paths.path_generated_thumbnails)
        return settings.paths.path_generated_thumbnails.joinpath(filename_sized)


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


async def read_image_by_size(filename: str, width: int | None, height: int | None, image_dal: ImageDAL) -> bytes:
    """return the image in specified size as bytes"""
    path = await get_image_path_by_size(filename=filename,
                                        width=width,
                                        height=height,
                                        image_dal=image_dal)

    if not path.is_file():
        # return default image on dev environment where most photos are missing
        if local_config.log_settings.ignore_missing_image_files:
            path = get_dummy_image_path_by_size(width=width, height=height)
        else:
            logger.error(err_msg := f'Image file not found: {path}')
            throw_exception(err_msg)

    async with aiofiles.open(path, 'rb') as file:
        image_bytes: bytes = await file.read()

    # with open(path, "rb") as image:
    #     image_bytes: bytes = image.read()

    return image_bytes


async def read_occurrence_thumbnail(gbif_id: int, occurrence_id: int, img_no: int, taxon_dal: TaxonDAL):
    taxon_occurrence_images: list[TaxonOccurrenceImage] = await taxon_dal.get_taxon_occurrence_image_by_filter(
        {'gbif_id': gbif_id, 'occurrence_id': occurrence_id, 'img_no': img_no})

    if not taxon_occurrence_images:
        logger.error(err_msg := f'Occurrence thumbnail file not found: {gbif_id}/{occurrence_id}/{img_no}')
        throw_exception(err_msg)

    assert len(taxon_occurrence_images) == 1
    taxon_occurrence_image = taxon_occurrence_images[0]

    # taxon_occurrence_image: TaxonOccurrenceImage = (db.query(TaxonOccurrenceImage).filter(
    #                                 TaxonOccurrenceImage.gbif_id == gbif_id,
    #                                 TaxonOccurrenceImage.occurrence_id == occurrence_id,
    #                                 TaxonOccurrenceImage.img_no == img_no).first())
    if not taxon_occurrence_image:
        logger.error(err_msg := f'Occurrence thumbnail file not found: {gbif_id}/{occurrence_id}/{img_no}')
        throw_exception(err_msg)

    path = settings.paths.path_generated_thumbnails_taxon.joinpath(taxon_occurrence_image.filename_thumbnail)
    if not path.is_file():
        # return default image on dev environment where most photos are missing
        if local_config.log_settings.ignore_missing_image_files:
            path = get_dummy_image_path_by_size(width=settings.images.size_thumbnail_image_taxon[0],
                                                height=settings.images.size_thumbnail_image_taxon[1])
        else:
            logger.error(err_msg := f'Occurence thumbnail file not found: {path}')
            throw_exception(err_msg)

    # with open(path, "rb") as image:
    #     image_bytes: bytes = image.read()

    async with aiofiles.open(path, 'rb') as file:
        image_bytes: bytes = await file.read()

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
                                   ignore_missing_image_files=local_config.log_settings.ignore_missing_image_files)
                count_generated += 1
                logger.info(f'Generated thumbnail in size {size} for {image.absolute_path}')

    logger.info(f'Thumbnail Generation - Count already existed: {count_already_existed}')
    logger.info(f'Thumbnail Generation - Count generated: {count_generated}')
    logger.info(f'Thumbnail Generation - Files not found: {count_files_not_found}')


async def trigger_generation_of_missing_thumbnails(background_tasks: BackgroundTasks, image_dal: ImageDAL) -> str:
    images: list[Image] = await image_dal.get_all_images()
    logger.info(msg := f"Generating thumbnails for {len(images)} images in "
                       f"sizes: {settings.images.sizes} in background.")
    # todo correct like that with async?
    background_tasks.add_task(_generate_missing_thumbnails, images)
    return msg


async def fetch_images_for_plant(plant: Plant, image_dal: ImageDAL) -> list[ImageCreateUpdate]:
    # for async, we need to reload the image relationships
    images = await image_dal.by_ids([i.id for i in plant.images])
    # todo switch to orm mode
    image_results = [_to_response_image(image) for image in images]
    return image_results


def _to_response_image(image: Image) -> ImageCreateUpdate:
    # todo swithc toorm mode
    # from sqlalchemy import inspect
    # ins = inspect(image)
    # if 'plants' in ins.unloaded or 'keywords' in ins.unloaded:
    #     a = 1

    k: ImageKeyword
    return ImageCreateUpdate(
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


async def fetch_untagged_images(image_dal: ImageDAL) -> list[ImageCreateUpdate]:
    untagged_images = await image_dal.get_untagged_images()
    return [_to_response_image(image) for image in untagged_images]


def _shorten_plant_name(plant_name: str) -> str:
    """shorten plant name to 20 chars for display in ui5 table"""
    return (plant_name[:settings.frontend.restrictions.length_shortened_plant_name_for_tag - 3] + '...'
            if len(plant_name) > settings.frontend.restrictions.length_shortened_plant_name_for_tag
            else plant_name)


async def _create_image(image_dal: ImageDAL,
                        relative_path: PurePath,
                        record_date_time: datetime,
                        description: str = None,
                        plants: list[Plant] = None,
                        keywords: Sequence[str] = (),
                        # events and taxa are saved elsewhere
                        ) -> Image:
    if await image_dal.get_image_by_relative_path(relative_path.as_posix()):
        # if db.query(Image).filter(Image.relative_path == relative_path.as_posix()).first():
        raise ValueError(f'Image already exists in db: {relative_path.as_posix()}')

    image = Image(relative_path=relative_path.as_posix(),
                  filename=relative_path.name,
                  record_date_time=record_date_time,
                  description=description,
                  plants=plants if plants else [],
                  )
    # get the image id
    await image_dal.create_image(image)

    if keywords:
        keywords_orm = [
            ImageKeyword(
                image_id=image.id,
                image=image,
                keyword=k) for k in keywords
        ]
        await image_dal.create_new_keywords_for_image(image, keywords_orm)
    return image

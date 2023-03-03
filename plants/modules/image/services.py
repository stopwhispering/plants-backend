from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
from fastapi import BackgroundTasks, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from plants import constants, local_config, settings
from plants.modules.image.exif_utils import read_record_datetime_from_exif_tags
from plants.modules.image.image_services_simple import resizing_required
from plants.modules.image.image_writer import ImageWriter
from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.image.schemas import FBImagePlantTag, ImageCreateUpdate
from plants.modules.image.util import (
    generate_thumbnail,
    generate_timestamp_filename,
    get_thumbnail_name,
    resize_image,
)
from plants.shared.message_services import throw_exception
from plants.shared.path_utils import get_generated_filename, with_suffix

if TYPE_CHECKING:
    from plants.modules.image.image_dal import ImageDAL
    from plants.modules.image.models import Image
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL
    from plants.modules.taxon.models import TaxonOccurrenceImage
    from plants.modules.taxon.taxon_dal import TaxonDAL

logger = logging.getLogger(__name__)

NOT_AVAILABLE_IMAGE_FILENAME = "not_available.png"


def _rename_plant_in_image_files(
    images: list[Image], exif: PhotoMetadataAccessExifTags
) -> None:
    for image in images:
        plant_names = [p.plant_name for p in image.plants]
        exif.rewrite_plant_assignments(
            absolute_path=image.absolute_path, plants=plant_names
        )


async def rename_plant_in_image_files(
    plant: Plant, plant_name_old: str, image_dal: ImageDAL
) -> int:
    """In each photo_file file that has the old plant name tagged, fit tag to the new
    plant name."""
    if not plant.images:
        logger.info(f"No photo_file tag to change for {plant_name_old}.")
    exif = PhotoMetadataAccessExifTags()
    # reload images to include their relationships (lazy loading not allowed in
    # async mode)
    images = await image_dal.by_ids([i.id for i in plant.images])
    await run_in_threadpool(_rename_plant_in_image_files, images=images, exif=exif)

    # note: there's no need to upload the cache as we did modify directly in the
    # cache above
    return len(images)


async def save_image_to_db(
    path: Path,
    image_dal: ImageDAL,
    plant_dal: PlantDAL,
    plant_ids: tuple[int] | None = None,
    keywords: tuple[str] | None = None,
) -> ImageCreateUpdate:
    # add to db
    record_datetime = read_record_datetime_from_exif_tags(absolute_path=path)
    plants = [await plant_dal.by_id(p) for p in plant_ids] if plant_ids else []
    image_writer = ImageWriter(plant_dal=plant_dal, image_dal=image_dal)
    image: Image = await image_writer.create_image_in_db(
        filename=path.name,
        record_date_time=record_datetime,
        keywords=keywords,
        plants=plants,
    )
    return _to_response_image(image)


async def save_image_file(
    file: UploadFile, plant_names: list[str], keywords: tuple[str] | None = None
) -> Path:
    """Save the files supplied as starlette uploadfiles on os; assign plants and
    keywords."""
    # save to file system
    filename_ = file.filename if file.filename else generate_timestamp_filename()
    path = settings.paths.path_original_photos_uploaded.joinpath(filename_)
    logger.info(f"Saving {path}.")

    async with aiofiles.open(path, "wb") as out_file:
        content = await file.read()  # async read
        await out_file.write(content)  # async write

    # resize file by lowering resolution if required
    if not settings.images.resizing_size:
        pass
    elif not resizing_required(path, settings.images.resizing_size):
        logger.info("No resizing required.")
    else:
        logger.info(f"Saving and resizing {path}.")
        resize_image(
            path=path,
            save_to_path=with_suffix(path, constants.RESIZE_SUFFIX),
            size=settings.images.resizing_size,
            quality=settings.images.jpg_quality,
        )
        path = with_suffix(path, constants.RESIZE_SUFFIX)

    # generate thumbnails for frontend display
    for size in settings.images.sizes:
        generate_thumbnail(
            image=path,
            size=size,
            path_thumbnail=settings.paths.path_generated_thumbnails,
            ignore_missing_image_files=(
                local_config.log_settings.ignore_missing_image_files
            ),
        )

    # save metadata in jpg exif tags
    # plants = [await plant_dal.by_id(p) for p in plant_ids]
    await PhotoMetadataAccessExifTags().save_photo_metadata(
        image_absolute_path=path,
        plant_names=plant_names,  # [p.plant_name for p in plants],
        keywords=list(keywords) if keywords else [],
        description="",
    )

    return path


async def delete_image_file_and_db_entries(image: Image, image_dal: ImageDAL) -> None:
    """Delete image file and entries in db."""
    if image.image_to_event_associations:
        logger.info(
            f"Deleting {len(image.image_to_event_associations)} associated Image to "
            f"Event associations."
        )
        await image_dal.delete_image_to_event_associations(
            image, image.image_to_event_associations
        )
        image.events = []
    if image.image_to_plant_associations:
        logger.info(
            f"Deleting {len(image.image_to_plant_associations)} associated Image to "
            f"Plant associations."
        )
        await image_dal.delete_image_to_plant_associations(
            image, image.image_to_plant_associations
        )
        image.plants = []
    if image.image_to_taxon_associations:
        logger.info(
            f"Deleting {len(image.image_to_taxon_associations)} associated Image to "
            f"Taxon associations."
        )
        await image_dal.delete_image_to_taxon_associations(
            image, image.image_to_taxon_associations
        )
        image.taxa = []
    if image.keywords:
        logger.info(f"Deleting {len(image.keywords)} associated Keywords.")
        await image_dal.delete_keywords_from_image(image, image.keywords)

    await image_dal.delete_image(image)

    old_path = image.absolute_path
    if not old_path.is_file():
        if local_config.log_settings.ignore_missing_image_files:
            logger.warning(f"Image file {old_path} to be deleted not found.")
            return
        logger.error(err_msg := f"File selected to be deleted not found: {old_path}")
        throw_exception(err_msg)

    new_path = settings.paths.path_deleted_photos.joinpath(old_path.name)
    try:
        # old_path.replace(new_path)
        os.replace(
            src=old_path, dst=new_path
        )  # silently overwrites if privileges are sufficient
    except OSError as e:
        logger.exception(
            err_msg := f"OSError when moving file {old_path} to {new_path}", exc_info=e
        )
        throw_exception(err_msg, description=f"Filename: {old_path.name}")
    logger.info(f"Moved file {old_path} to {new_path}")


# def _get_sized_image_path(filename: str, size_px: int) -> Path:
#     """return the path to the image file with the given pixel size"""
#


async def get_image_path_by_size(
    filename: str, size: tuple[int, int] | None, image_dal: ImageDAL
) -> Path:
    if size is None:
        # get image db entry for the directory it is stored at in local filesystem
        image: Image = await image_dal.get_image_by_filename(filename=filename)
        return Path(image.absolute_path)

    # the pixel size is part of the resized images' filenames rem size must be
    # converted to px
    filename_sized = get_generated_filename(filename, size)
    return settings.paths.path_generated_thumbnails.joinpath(filename_sized)


async def get_occurrence_thumbnail_path(
    gbif_id: int, occurrence_id: int, img_no: int, taxon_dal: TaxonDAL
) -> Path:
    taxon_occurrence_images: list[
        TaxonOccurrenceImage
    ] = await taxon_dal.get_taxon_occurrence_image_by_filter(
        {"gbif_id": gbif_id, "occurrence_id": occurrence_id, "img_no": img_no}
    )

    if not taxon_occurrence_images:
        logger.error(
            err_msg := f"Occurrence thumbnail file not found: {gbif_id}/"
            f"{occurrence_id}/{img_no}"
        )
        throw_exception(err_msg)

    if len(taxon_occurrence_images) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Multiple  occurrence images found for {gbif_id}/"
            f"{occurrence_id}/{img_no}",
        )
    taxon_occurrence_image = taxon_occurrence_images[0]

    if not taxon_occurrence_image:
        logger.error(
            err_msg := f"Occurrence thumbnail file not found: {gbif_id}/"
            f"{occurrence_id}/{img_no}"
        )
        throw_exception(err_msg)

    return settings.paths.path_generated_thumbnails_taxon.joinpath(
        taxon_occurrence_image.filename_thumbnail
    )


def _generate_missing_thumbnails(images: list[Image]) -> None:
    count_already_existed = 0
    count_generated = 0
    count_files_not_found = 0
    image: Image
    for _i, image in enumerate(images):
        if not image.absolute_path.is_file():
            count_files_not_found += 1
            logger.error(f"File not found: {image.absolute_path}")
            continue

        for size in settings.images.sizes:
            path_thumbnail = settings.paths.path_generated_thumbnails.joinpath(
                get_thumbnail_name(image.filename, size)
            )
            if path_thumbnail.is_file():
                count_already_existed += 1
            else:
                generate_thumbnail(
                    image=image.absolute_path,
                    size=size,
                    path_thumbnail=settings.paths.path_generated_thumbnails,
                    ignore_missing_image_files=(
                        local_config.log_settings.ignore_missing_image_files
                    ),
                )
                count_generated += 1
                logger.info(
                    f"Generated thumbnail in size {size} for {image.absolute_path}"
                )

    logger.info(
        f"Thumbnail Generation - Count already existed: {count_already_existed}"
    )
    logger.info(f"Thumbnail Generation - Count generated: {count_generated}")
    logger.info(f"Thumbnail Generation - Files not found: {count_files_not_found}")


async def trigger_generation_of_missing_thumbnails(
    background_tasks: BackgroundTasks, image_dal: ImageDAL
) -> str:
    images: list[Image] = await image_dal.get_all_images()
    logger.info(
        msg := f"Generating thumbnails for {len(images)} images in "
        f"sizes: {settings.images.sizes} in background."
    )
    # todo correct like that with async?
    background_tasks.add_task(_generate_missing_thumbnails, images)
    return msg


async def fetch_images_for_plant(
    plant: Plant, image_dal: ImageDAL
) -> list[ImageCreateUpdate]:
    # for async, we need to reload the image relationships
    images = await image_dal.by_ids([i.id for i in plant.images])
    # todo switch to orm mode
    return [_to_response_image(image) for image in images]


def _to_response_image(image: Image) -> ImageCreateUpdate:
    # todo swithc toorm mode
    # from sqlalchemy import inspect
    # ins = inspect(image)
    # if 'plants' in ins.unloaded or 'keywords' in ins.unloaded:
    #     a = 1

    return ImageCreateUpdate(
        id=image.id,
        filename=image.filename or "",
        keywords=[{"keyword": k.keyword} for k in image.keywords],
        plants=[
            FBImagePlantTag(
                plant_id=p.id,
                plant_name=p.plant_name,
                plant_name_short=_shorten_plant_name(p.plant_name),
                # key=p.plant_name,
                # text=p.plant_name,
            )
            for p in image.plants
        ],
        description=image.description,
        record_date_time=image.record_date_time,
    )


async def fetch_untagged_images(image_dal: ImageDAL) -> list[ImageCreateUpdate]:
    untagged_images = await image_dal.get_untagged_images()
    return [_to_response_image(image) for image in untagged_images]


def _shorten_plant_name(plant_name: str) -> str:
    """Shorten plant name to 20 chars for display in ui5 table."""
    return (
        plant_name[
            : settings.frontend.restrictions.length_shortened_plant_name_for_tag - 3
        ]
        + "..."
        if len(plant_name)
        > settings.frontend.restrictions.length_shortened_plant_name_for_tag
        else plant_name
    )

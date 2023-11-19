from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks, HTTPException
from starlette.concurrency import run_in_threadpool

from plants import local_config, settings
from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.image.util import (
    generate_thumbnail,
    get_thumbnail_name,
)
from plants.shared.message_services import throw_exception
from plants.shared.path_utils import get_generated_filename

if TYPE_CHECKING:
    from pathlib import Path

    from plants.modules.image.image_dal import ImageDAL
    from plants.modules.image.models import Image
    from plants.modules.plant.models import Plant
    from plants.modules.taxon.models import TaxonOccurrenceImage
    from plants.modules.taxon.taxon_dal import TaxonDAL

logger = logging.getLogger(__name__)

NOT_AVAILABLE_IMAGE_FILENAME = "not_available.png"


def _rename_plant_in_image_files(images: list[Image], exif: PhotoMetadataAccessExifTags) -> None:
    for image in images:
        plant_names = [p.plant_name for p in image.plants]
        exif.rewrite_plant_assignments(absolute_path=image.absolute_path, plants=plant_names)


async def rename_plant_in_image_files(
    plant: Plant, plant_name_old: str, image_dal: ImageDAL
) -> int:
    """In each photo_file file that has the old plant name tagged, fit tag to the new plant name."""
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


async def delete_image_file_and_db_entries(image: Image, image_dal: ImageDAL) -> None:
    """Delete image file and entries in db."""

    # delete in db, cascadedes to image_to_event_associations, image_to_plant_associations,
    # and keywords
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
        old_path.replace(target=new_path)
    except OSError as err:
        logger.exception(
            err_msg := f"OSError when moving file {old_path} to {new_path}", exc_info=err
        )
        throw_exception(err_msg, description=f"Filename: {old_path.name}")
    logger.info(f"Moved file {old_path} to {new_path}")


async def get_image_path_by_size(image: Image, size: tuple[int, int] | None) -> Path:
    if size is None:
        # get image db entry for the directory it is stored at in local filesystem
        # image: Image = await image_dal.get_image_by_filename(filename=filename)
        return image.absolute_path

    # the pixel size is part of the resized images' filenames rem size must be
    # converted to px
    filename_sized = get_generated_filename(image.filename, size)
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
            detail=f"Multiple  occurrence images found for {gbif_id}/" f"{occurrence_id}/{img_no}",
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
                filename_thumb = get_thumbnail_name(image.filename, size)
                path_saved = generate_thumbnail(
                    image=image.absolute_path,
                    thumbnail_folder=settings.paths.path_generated_thumbnails,
                    size=size,
                    thumbnail_filename=filename_thumb,
                    ignore_missing_image_files=(
                        local_config.log_settings.ignore_missing_image_files
                    ),
                )
                if path_saved:
                    count_generated += 1
                    logger.info(f"Generated thumbnail {path_saved}.")

    logger.info(f"Thumbnail Generation - Count already existed: {count_already_existed}")
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
    background_tasks.add_task(_generate_missing_thumbnails, images)
    return msg


async def fetch_images_for_plant(plant: Plant, image_dal: ImageDAL) -> list[Image]:
    # for async, we need to reload the image relationships
    return await image_dal.by_ids([i.id for i in plant.images])


async def fetch_untagged_images(image_dal: ImageDAL) -> list[Image]:
    return await image_dal.get_untagged_images()

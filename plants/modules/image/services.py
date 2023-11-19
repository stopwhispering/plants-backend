from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aiofiles
from fastapi import BackgroundTasks, HTTPException, UploadFile
from PIL import Image as PilImage
from starlette.concurrency import run_in_threadpool

from plants import constants, local_config, settings
from plants.modules.image.exif_utils import read_record_datetime_from_exif_tags
from plants.modules.image.image_services_simple import (
    is_resizing_required,
    original_image_file_exists,
    remove_image_from_filesystem,
)
from plants.modules.image.image_writer import ImageWriter
from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.image.util import (
    generate_thumbnail,
    generate_thumbnail_for_pil_image,
    generate_timestamp_filename,
    get_thumbnail_name,
    resize_and_save,
)
from plants.shared.message_services import throw_exception
from plants.shared.path_utils import get_generated_filename, with_suffix

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from plants.modules.image.image_dal import ImageDAL
    from plants.modules.image.models import Image
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL
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


async def save_image_to_db(
    path: Path,
    image_dal: ImageDAL,
    plant_dal: PlantDAL,
    plant_ids: Sequence[int] | None = None,
    keywords: Sequence[str] | None = None,
) -> Image:
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
    return image


async def save_upload_image(
    upload_image: UploadImage, plant_names: list[str], keywords: Sequence[str] | None = None
) -> Path:
    """Save the files supplied as starlette uploadfiles on os; assign plants and keywords."""

    # resize by lowering resolution if required
    if not upload_image.resizing_required:
        logger.info(f"Saving {upload_image.path}. No resizing required.")
        async with aiofiles.open(upload_image.path, "wb") as out_file:
            await out_file.write(upload_image.file_content)  # async write

    else:
        logger.info(f"Resizing and Saving to {upload_image.path}.")
        await resize_and_save(
            upload_image=upload_image,
            size=settings.images.resizing_size,
            quality=settings.images.jpg_quality,
        )

    # generate thumbnails for frontend display
    for size in settings.images.sizes:
        filename_thumb = get_thumbnail_name(upload_image.path.name, size)
        generate_thumbnail_for_pil_image(
            pil_image=upload_image.pil_image,
            thumbnail_folder=settings.paths.path_generated_thumbnails,
            size=size,
            thumbnail_filename=filename_thumb,
            ignore_missing_image_files=local_config.log_settings.ignore_missing_image_files,
        )

    # save metadata in jpg exif tags
    await PhotoMetadataAccessExifTags().save_photo_metadata(
        image_absolute_path=upload_image.path,
        plant_names=plant_names,
        keywords=list(keywords) if keywords else [],
        description="",
    )

    return upload_image.path


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


@dataclass
class UploadImage:
    pil_image: PilImage.Image
    file_content: bytes
    path: Path
    resizing_required: bool


async def handle_image_uploads(
    files: list[UploadFile],
    plants: list[Plant],
    keywords: list[str],
    plant_dal: PlantDAL,
    image_dal: ImageDAL,
) -> tuple[list[Image], list[str], list[str], list[UploadFile]]:
    # for image that need a resize, we will add a suffix to the filename

    upload_images: list[UploadImage] = []
    for file in files:
        file_content: bytes = await file.read()
        pil_image: PilImage.Image = PilImage.open(io.BytesIO(file_content))

        filename = file.filename or generate_timestamp_filename()
        resizing_required = await is_resizing_required(pil_image, settings.images.resizing_size)
        if resizing_required:
            filename = with_suffix(filename, constants.RESIZE_SUFFIX)
        path = settings.paths.path_original_photos_uploaded.joinpath(filename)

        upload_images.append(
            UploadImage(
                pil_image=pil_image,
                file_content=file_content,
                path=path,
                resizing_required=resizing_required,
            )
        )

    # remove duplicates (filename already exists in file system)
    duplicate_filenames, warnings, upload_images = await remove_images_already_existing(
        all_upload_images=upload_images, image_dal=image_dal
    )

    # schedule and run tasks to save images concurrently
    # (unfortunately, we can't include the db saving here as SQLAlchemy AsyncSessions
    # don't allow
    # to be run concurrently - at least writing stops with "Session is already flushing"
    # InvalidRequestError) (2023-02)
    async with asyncio.TaskGroup() as task_group:
        tasks = [
            task_group.create_task(
                save_upload_image(
                    upload_image=upload_image,
                    plant_names=[plant.plant_name for plant in plants],
                    keywords=keywords,
                )
            )
            for upload_image in upload_images
        ]
    paths: list[Path] = [task.result() for task in tasks]

    images: list[Image] = []
    for path in paths:
        images.append(
            await save_image_to_db(
                path=path,
                image_dal=image_dal,
                plant_dal=plant_dal,
                plant_ids=[plant.id for plant in plants],
                keywords=keywords,
            )
        )
    return images, duplicate_filenames, warnings, files


async def remove_images_already_existing(
    all_upload_images: list[UploadImage], image_dal: ImageDAL
) -> tuple[list[str], list[str], list[UploadImage]]:
    """Iterates over upload images, checks whether a file with that name already exists in
    filesystem and/or in database.

    - if we have an orphaned file in filesystem, missing in database, it will be
    deleted with a message
    - if we have have an orphaned entry in database, missing in filesystem, it will
    be deleted with a messasge
    - if existent in both filesystem and db, remove it from  files list with a message
    """
    duplicate_filenames = []
    warnings = []
    upload_images = all_upload_images[:]
    for photo_upload in upload_images[:]:  # need to loop on copy if we want to delete within loop
        exists_in_filesystem = original_image_file_exists(filename=photo_upload.path.name)
        exists_in_db = await image_dal.image_exists(filename=photo_upload.path.name)
        if exists_in_filesystem and not exists_in_db:
            remove_image_from_filesystem(filename=photo_upload.path.name)
            logger.warning(
                warning := "Found orphaned image {photo_upload.filename} in "
                "filesystem, "
                "but not in database. Deleted image file."
            )
            warnings.append(warning)
        elif exists_in_db and not exists_in_filesystem:
            await image_dal.delete_image_by_filename(filename=photo_upload.path.name)
            logger.warning(
                warning := f"Found orphaned db entry for uploaded image  "
                f"{photo_upload.path.name} with no "
                f"corresponsing file. Removed db entry."
            )
            warnings.append(warning)
        # if path.is_file() or with_suffix(path, suffix).is_file():
        elif exists_in_filesystem and exists_in_db:
            upload_images.remove(photo_upload)
            duplicate_filenames.append(photo_upload.path.name)
            logger.warning(f"Skipping file upload (duplicate) for: {photo_upload.path.name}")
    return duplicate_filenames, warnings, upload_images

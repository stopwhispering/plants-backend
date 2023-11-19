from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aiofiles
from PIL import Image as PilImage

from plants import constants, local_config, settings
from plants.modules.image.exif_utils import read_record_datetime_from_exif_tags
from plants.modules.image.image_services_simple import (
    is_resizing_required,
    original_image_file_exists,
    remove_image_from_filesystem,
)
from plants.modules.image.image_writer import ImageWriter
from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.image.services import logger
from plants.modules.image.util import (
    generate_thumbnail_for_pil_image,
    generate_timestamp_filename,
    get_thumbnail_name,
    resize_and_save,
)
from plants.shared.path_utils import with_suffix

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from fastapi import UploadFile

    from plants.modules.image.image_dal import ImageDAL
    from plants.modules.image.models import Image
    from plants.modules.plant.models import Plant
    from plants.modules.plant.plant_dal import PlantDAL


@dataclass
class UploadImage:
    pil_image: PilImage.Image
    file_content: bytes
    path: Path
    resizing_required: bool


async def _extract_images_from_upload_files(files: list[UploadFile]) -> list[UploadImage]:
    upload_images: list[UploadImage] = []
    for file in files:
        file_content: bytes = await file.read()
        pil_image: PilImage.Image = PilImage.open(io.BytesIO(file_content))

        filename = file.filename or generate_timestamp_filename()
        resizing_required = is_resizing_required(pil_image, settings.images.resizing_size)
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
    return upload_images


async def handle_image_uploads(
    files: list[UploadFile],
    plants: list[Plant],
    keywords: list[str],
    plant_dal: PlantDAL,
    image_dal: ImageDAL,
) -> tuple[list[Image], list[str], list[str], list[UploadFile]]:
    upload_images = await _extract_images_from_upload_files(files)

    # remove duplicates (filename already exists in file system)
    duplicate_filenames, warnings, upload_images = await _identify_already_existing(
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


async def _identify_already_existing(
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

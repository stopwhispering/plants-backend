from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, UploadFile
from starlette.responses import FileResponse

from plants.dependencies import (
    get_image_dal,
    get_plant_dal,
    get_taxon_dal,
    valid_image,
    valid_plant,
)
from plants.exceptions import ImageFileNotFoundError
from plants.modules.event.schemas import FImagesToDelete
from plants.modules.image.image_dal import ImageDAL
from plants.modules.image.image_writer import ImageWriter
from plants.modules.image.models import Image
from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.image.schemas import (
    BImageUpdated,
    BResultsImageDeleted,
    BResultsImageResource,
    BResultsImagesUploaded,
    FImageUploadedMetadata,
    ImageRead,
)
from plants.modules.image.services import (
    delete_image_file_and_db_entries,
    fetch_images_for_plant,
    fetch_untagged_images,
    get_image_path_by_size,
    get_occurrence_thumbnail_path,
    handle_image_uploads,
    trigger_generation_of_missing_thumbnails,
)
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.enums import MajorResource, MessageType
from plants.shared.message_schemas import BConfirmation, BSaveConfirmation
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["images"],
    responses={404: {"description": "Not found"}},
)


@router.get("/plants/{plant_id}/images/", response_model=list[ImageRead])
async def get_images_for_plant(
    plant: Plant = Depends(valid_plant),
    image_dal: ImageDAL = Depends(get_image_dal),
) -> Any:
    """Get photo_file information for requested plant_id including (other) plants and keywords."""
    images = await fetch_images_for_plant(plant, image_dal=image_dal)
    logger.info(f"Returned {len(images)} images for plant {plant.id}.")
    return images


@router.post("/plants/{plant_id}/images/", response_model=BResultsImagesUploaded)
async def upload_images_plant(
    request: Request,
    plant: Plant = Depends(valid_plant),
    image_dal: ImageDAL = Depends(get_image_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    """Upload images and directly assign them to supplied plant; no keywords included.

    # the ui5 uploader control does somehow not work with the expected form/multipart
    format expected
    # via fastapi argument files = List[UploadFile] = File(...)
    # therefore, we directly go on the starlette request object
    """
    form = await request.form()
    # noinspection PyTypeChecker
    files: list[UploadFile] = form.getlist("files[]")  # type: ignore[assignment]
    images, duplicate_filenames, warnings, files = await handle_image_uploads(
        files=files,
        plants=[plant],
        keywords=[],
        plant_dal=plant_dal,
        image_dal=image_dal,
    )

    desc = f"Saved: {[p.filename for p in files]}.\n" f"Skipped Duplicates: {duplicate_filenames}."
    if warnings:
        warnings_s = "\n".join(warnings)
        desc += f"\n{warnings_s}"
    message = get_message(
        msg := (
            (f"Saved {len(files)} images. " "Duplicates found.") if duplicate_filenames else ""
        ),
        message_type=MessageType.WARNING if duplicate_filenames else MessageType.INFORMATION,
        description=desc,
    )
    logger.info(msg)
    return {"action": "Uploaded", "message": message, "images": images}


@router.get("/images/untagged/", response_model=BResultsImageResource)
async def get_untagged_images(image_dal: ImageDAL = Depends(get_image_dal)) -> Any:
    """Get images with no plants assigned, yet."""
    untagged_images: list[Image] = await fetch_untagged_images(image_dal=image_dal)
    logger.info(msg := f"Returned {len(untagged_images)} images.")
    return {
        "action": "Get untagged images",
        "ImagesCollection": untagged_images,
        "message": get_message(msg, description=f"Count: {len(untagged_images)}"),
    }


@router.put("/images/", response_model=BSaveConfirmation)
async def update_images(
    modified_ext: BImageUpdated,
    image_dal: ImageDAL = Depends(get_image_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    """Modify existing photo_file's metadata."""
    logger.info(
        f"Saving updates for {len(modified_ext.ImagesCollection)} images in db and " f"exif tags."
    )
    for image_ext in modified_ext.ImagesCollection:
        # alter metadata in jpg exif tags
        logger.info(f"Updating {image_ext.filename}")
        image = await image_dal.by_id(image_ext.id)
        await PhotoMetadataAccessExifTags().save_photo_metadata(
            image_absolute_path=image.absolute_path,
            plant_names=[p.plant_name for p in image_ext.plants],
            keywords=[k.keyword for k in image_ext.keywords],
            description=image_ext.description or "",
        )
        image = await image_dal.get_image_by_filename(filename=image_ext.filename)
        image_writer = ImageWriter(plant_dal=plant_dal, image_dal=image_dal)
        await image_writer.update_image_if_altered(
            image=image,
            description=image_ext.description,
            plant_ids=[plant.plant_id for plant in image_ext.plants],
            keywords=[k.keyword for k in image_ext.keywords],
        )

    return {
        "resource": MajorResource.IMAGE,
        "message": get_message(f"Saved updates for {len(modified_ext.ImagesCollection)} images."),
    }


@router.post("/images/", response_model=BResultsImagesUploaded)
async def upload_images(
    request: Request,
    image_dal: ImageDAL = Depends(get_image_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    """upload new photo_file(s)"""
    # the ui5 uploader control does somehow not work with the expected form/multipart
    # format expected
    # via fastapi argument files = List[UploadFile] = File(...)
    # therefore, we directly go on the starlette request object
    form = await request.form()
    additional_data = json.loads(form.get("files-data"))  # type: ignore[arg-type]
    # noinspection PyTypeChecker
    files: list[UploadFile] = form.getlist("files[]")  # type: ignore[assignment]

    # validate arguments manually as pydantic doesn't trigger here
    additional_data_ = FImageUploadedMetadata(**additional_data)

    plants = [(await plant_dal.by_id(plant_id)) for plant_id in additional_data_.plants]
    images, duplicate_filenames, warnings, files = await handle_image_uploads(
        files=files,
        plants=plants,
        keywords=additional_data_.keywords,
        plant_dal=plant_dal,
        image_dal=image_dal,
    )

    desc = f"Saved: {[p.filename for p in files]}." f"\nSkipped Duplicates: {duplicate_filenames}."
    if warnings:
        warnings_s = "\n".join(warnings)
        desc += f"\n{warnings_s}"

    message = get_message(
        msg := f"Saved {len(files)} images."
        + (" Duplicates found." if duplicate_filenames else ""),
        message_type=MessageType.WARNING if duplicate_filenames else MessageType.INFORMATION,
        description=f"Saved: {[p.filename for p in files]}."
        f"\nSkipped Duplicates: {duplicate_filenames}.",
    )
    logger.info(msg)
    return {"action": "Uploaded", "message": message, "images": images}


@router.delete("/images/", response_model=BResultsImageDeleted)
async def delete_image(
    image_container: FImagesToDelete, image_dal: ImageDAL = Depends(get_image_dal)
) -> Any:
    """move the file that should be deleted to another folder (not actually deleted, currently)"""
    deleted_files: list[str] = []
    for image_to_delete in image_container.images:
        image = await image_dal.by_id(image_id=image_to_delete.id)
        deleted_files.append(image.filename)
        await delete_image_file_and_db_entries(image=image, image_dal=image_dal)

    return {
        "action": "Deleted",
        "message": get_message(
            f"Deleted {len(image_container.images)} image(s)",
            description=f"Filenames: {deleted_files}",
        ),
    }


@router.get(
    "/occurrence_thumbnail",
    # Prevent FastAPI from adding "application/json" as an additional
    # response media type in the autogenerated OpenAPI specification.
    response_class=FileResponse,
)
async def get_occurrence_thumbnail(
    gbif_id: int,
    occurrence_id: int,
    img_no: int,
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
) -> Any:
    path: Path = await get_occurrence_thumbnail_path(
        gbif_id=gbif_id, occurrence_id=occurrence_id, img_no=img_no, taxon_dal=taxon_dal
    )

    # media_type here sets the media type of the actual response sent to the client.
    return FileResponse(path=path, media_type="image/jpeg", filename=path.name)


@router.get("/image/{image_id}", response_class=FileResponse)
async def get_image(
    image: Image = Depends(valid_image),
    width: int | None = None,
    height: int | None = None,
) -> Any:
    size = (width, height) if width and height else None
    image_path = await get_image_path_by_size(image=image, size=size)

    if not image_path.is_file():
        raise ImageFileNotFoundError(filename=image.filename)

    # media_type here sets the media type of the actual response sent to the client.
    return FileResponse(path=image_path, media_type="image/jpeg", filename=image_path.name)


@router.post("/generate_missing_thumbnails", response_model=BConfirmation)
async def trigger_generate_missing_thumbnails(
    background_tasks: BackgroundTasks, image_dal: ImageDAL = Depends(get_image_dal)
) -> Any:
    """Trigger the generation of missing thumbnails for occurrences."""
    msg = await trigger_generation_of_missing_thumbnails(
        image_dal=image_dal, background_tasks=background_tasks
    )
    return {
        "action": "Triggering generation of missing thumbnails",
        "message": get_message(msg),
    }

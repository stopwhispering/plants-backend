from typing import List
import json
from sqlalchemy.orm import Session
import logging
from pydantic.error_wrappers import ValidationError
from fastapi import UploadFile, BackgroundTasks
from fastapi import APIRouter, Depends, Request
from starlette.responses import Response

from plants import constants
from plants.modules.image.models import Image, update_image_if_altered
from plants.modules.image.services import (
    save_image_files, delete_image_file_and_db_entries, read_image_by_size,
    read_occurrence_thumbnail, trigger_generation_of_missing_thumbnails, fetch_images_for_plant, fetch_untagged_images)
from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.plant.models import Plant
from plants.shared.message_services import throw_exception, get_message
from plants.dependencies import get_db, valid_plant
from plants.modules.image.schemas import (BResultsImageResource, BImageUpdated, FImageUploadedMetadata,
                                          BResultsImagesUploaded, FBImages, FBImage)
from plants.modules.image.image_services_simple import remove_files_already_existing
from plants.modules.event.schemas import FImagesToDelete
from plants.modules.image.schemas import BResultsImageDeleted
from plants.shared.message_schemas import BMessageType, BSaveConfirmation, FBMajorResource, BConfirmation

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["images"],
    responses={404: {"description": "Not found"}},
)


@router.get("/plants/{plant_id}/images/", response_model=FBImages)
async def get_images_for_plant(plant: Plant = Depends(valid_plant)):
    """
    get photo_file information for requested plant_id including (other) plants and keywords
    """
    images = fetch_images_for_plant(plant)
    logger.info(f'Returned {len(images)} images for plant {plant.id}.')
    return images


@router.post("/plants/{plant_id}/images/", response_model=BResultsImagesUploaded)
async def upload_images_plant(request: Request, plant: Plant = Depends(valid_plant), db: Session = Depends(get_db)):
    """
    upload images and directly assign them to supplied plant; no keywords included
    # the ui5 uploader control does somehow not work with the expected form/multipart format expected
    # via fastapi argument files = List[UploadFile] = File(...)
    # therefore, we directly go on the starlette request object
    """
    form = await request.form()
    # noinspection PyTypeChecker
    files: List[UploadFile] = form.getlist('files[]')

    # remove duplicates (filename already exists in file system)
    duplicate_filenames, warnings = remove_files_already_existing(files, constants.RESIZE_SUFFIX, db=db)

    images: list[FBImage] = await save_image_files(files=files,
                                                   db=db,
                                                   plant_ids=(plant.id,),
                                                   )

    desc = (f'Saved: {[p.filename for p in files]}.'
            f'\nSkipped Duplicates: {duplicate_filenames}.')
    if warnings:
        warnings_s = '\n'.join(warnings)
        desc += f'\n{warnings_s}'
    message = get_message(msg := f'Saved {len(files)} images.' + (' Duplicates found.' if duplicate_filenames else ''),
                          message_type=BMessageType.WARNING if duplicate_filenames else BMessageType.INFORMATION,
                          description=desc)
    logger.info(msg)
    return {'action': 'Uploaded',
            'message': message,
            'images': images
            }


@router.get("/images/untagged/", response_model=BResultsImageResource)
async def get_untagged_images(db: Session = Depends(get_db)):
    """
    get images with no plants assigned, yet
    """
    untagged_images: list[FBImage] = fetch_untagged_images(db=db)
    logger.info(msg := f'Returned {len(untagged_images)} images.')
    return {'ImagesCollection': untagged_images,
            'message': get_message(msg,
                                   description=f'Count: {len(untagged_images)}')
            }


@router.put("/images/", response_model=BSaveConfirmation)
async def update_images(modified_ext: BImageUpdated, db: Session = Depends(get_db)):
    """
    modify existing photo_file's metadata
    """
    logger.info(f"Saving updates for {len(modified_ext.ImagesCollection.__root__)} images in db and exif tags.")
    for image_ext in modified_ext.ImagesCollection.__root__:
        # alter metadata in jpg exif tags
        logger.info(f'Updating {image_ext.filename}')
        PhotoMetadataAccessExifTags().save_photo_metadata(image_id=image_ext.id,
                                                          plant_names=[p.plant_name for p in image_ext.plants],
                                                          keywords=[k.keyword for k in image_ext.keywords],
                                                          description=image_ext.description or '',
                                                          db=db)
        image = Image.get_image_by_filename(filename=image_ext.filename, db=db)
        update_image_if_altered(image=image,
                                description=image_ext.description,
                                plant_ids=[plant.plant_id for plant in image_ext.plants],
                                keywords=[k.keyword for k in image_ext.keywords],
                                db=db)

    db.commit()
    return {'resource': FBMajorResource.IMAGE,
            'message': get_message(f"Saved updates for {len(modified_ext.ImagesCollection.__root__)} images.")
            }


@router.post("/images/", response_model=BResultsImagesUploaded)
async def upload_images(request: Request, db: Session = Depends(get_db)):
    """upload new photo_file(s)"""
    # the ui5 uploader control does somehow not work with the expected form/multipart format expected
    # via fastapi argument files = List[UploadFile] = File(...)
    # therefore, we directly go on the starlette request object
    form = await request.form()
    additional_data = json.loads(form.get('files-data'))
    # noinspection PyTypeChecker
    files: List[UploadFile] = form.getlist('files[]')

    # validate arguments manually as pydantic doesn't trigger here
    try:
        FImageUploadedMetadata(**additional_data)
    except ValidationError as err:
        throw_exception(str(err), request=request)

    # remove duplicates (filename already exists in file system)
    duplicate_filenames, warnings = remove_files_already_existing(files, constants.RESIZE_SUFFIX, db=db)

    images: list[FBImage] = await save_image_files(files=files,
                                                   db=db,
                                                   plant_ids=additional_data['plants'],
                                                   keywords=additional_data['keywords'])

    desc = (f'Saved: {[p.filename for p in files]}.'
            f'\nSkipped Duplicates: {duplicate_filenames}.')
    if warnings:
        warnings_s = '\n'.join(warnings)
        desc += f'\n{warnings_s}'

    message = get_message(msg := f'Saved {len(files)} images.' + (' Duplicates found.' if duplicate_filenames else ''),
                          message_type=BMessageType.WARNING if duplicate_filenames else BMessageType.INFORMATION,
                          description=f'Saved: {[p.filename for p in files]}.'
                                      f'\nSkipped Duplicates: {duplicate_filenames}.')
    logger.info(msg)
    return {'action': 'Uploaded',
            'message': message,
            'images': images
            }


@router.delete("/images/", response_model=BResultsImageDeleted)
async def delete_image(image_container: FImagesToDelete, db: Session = Depends(get_db)):
    """move the file that should be deleted to another folder (not actually deleted, currently)"""
    for image_to_delete in image_container.images:
        image = Image.get_image_by_id(id_=image_to_delete.id, db=db)
        if image.filename != image_to_delete.filename:
            logger.error(err_msg := f'Image {image.id} has unexpected filename: {image.filename}. '
                                    f'Expected filename: {image_to_delete.filename}. Analyze this inconsistency!')
            throw_exception(err_msg)

        delete_image_file_and_db_entries(image=image, db=db)

    db.commit()
    deleted_files = [image.filename for image in image_container.images]
    return {
        'action': 'Deleted',
        'message': get_message(f'Deleted {len(image_container.images)} image(s)',
                               description=f'Filenames: {deleted_files}')
    }


@router.get("/photo",
            # Prevent FastAPI from adding "application/json" as an additional
            # response media type in the autogenerated OpenAPI specification.
            response_class=Response)
def get_photo(filename: str, width: int = None, height: int = None, db: Session = Depends(get_db)):
    image_bytes: bytes = read_image_by_size(filename=filename, db=db, width=width, height=height)

    # media_type here sets the media type of the actual response sent to the client.
    return Response(content=image_bytes, media_type="image/png")


@router.get("/occurrence_thumbnail",
            # Prevent FastAPI from adding "application/json" as an additional
            # response media type in the autogenerated OpenAPI specification.
            response_class=Response)
def get_occurrence_thumbnail(gbif_id: int, occurrence_id: int, img_no: int, db: Session = Depends(get_db)):
    image_bytes: bytes = read_occurrence_thumbnail(gbif_id=gbif_id,
                                                   occurrence_id=occurrence_id,
                                                   img_no=img_no,
                                                   db=db)

    # media_type here sets the media type of the actual response sent to the client.
    return Response(content=image_bytes, media_type="image/png")


@router.post("/generate_missing_thumbnails", response_model=BConfirmation)
async def trigger_generate_missing_thumbnails(background_tasks: BackgroundTasks,
                                              db: Session = Depends(get_db)):
    """trigger the generation of missing thumbnails for occurrences"""
    msg = trigger_generation_of_missing_thumbnails(db=db, background_tasks=background_tasks)
    return {
        'action': 'Triggering generation of missing thumbnails',
        'message': get_message(msg)
    }

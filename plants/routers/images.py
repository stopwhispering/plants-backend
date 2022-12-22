from typing import List
import json
from sqlalchemy.orm import Session
import logging
from pydantic.error_wrappers import ValidationError
from fastapi import UploadFile, BackgroundTasks
from fastapi import APIRouter, Depends, Request
from starlette.responses import Response

from plants.constants import RESIZE_SUFFIX
from plants.models.image_models import Image, update_image_if_altered, ImageKeyword
from plants.services.image_services import save_image_files, delete_image_file_and_db_entries, read_image_by_size, \
    read_occurrence_thumbnail, trigger_generation_of_missing_thumbnails
from plants.services.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.util.ui_utils import PMessageType, get_message, throw_exception
from plants.dependencies import get_db
from plants.models.plant_models import Plant
from plants.validation.image_validation import (PResultsImageResource, PImageUpdated, PImageUploadedMetadata, PImage,
                                                PImagePlantTag, PResultsImagesUploaded, PImages)
from plants.services.image_services_simple import remove_files_already_existing
from plants.validation.event_validation import PImagesDelete
from plants.validation.image_validation import PResultsImageDeleted
from plants.validation.message_validation import PConfirmation, PMessage

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["images"],
    responses={404: {"description": "Not found"}},
)


@router.get("/plants/{plant_id}/images/", response_model=PImages)
async def get_images_plant(plant_id: int, db: Session = Depends(get_db)):
    """
    get photo_file information for requested plant_id including (other) plants and keywords
    """
    plant = Plant.get_plant_by_plant_id(plant_id, db=db, raise_exception=True)
    photo_files_ext = [_to_response_image(image) for image in plant.images]

    logger.info(f'Returned {len(photo_files_ext)} images for {plant_id} ({plant.plant_name}).')
    return photo_files_ext


@router.post("/plants/{plant_id}/images/", response_model=PResultsImagesUploaded)
async def upload_images_plant(plant_id: int, request: Request, db: Session = Depends(get_db)):
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
    duplicate_filenames = remove_files_already_existing(files, RESIZE_SUFFIX)

    images: List[Image] = await save_image_files(files=files,
                                                 db=db,
                                                 plant_ids=(plant_id,),
                                                 )
    images_ext = [_to_response_image(i) for i in images]

    msg = get_message(f'Saved {len(files)} images.' + (' Duplicates found.' if duplicate_filenames else ''),
                      message_type=PMessageType.WARNING if duplicate_filenames else PMessageType.INFORMATION,
                      description=f'Saved: {[p.filename for p in files]}.'
                                  f'\nSkipped Duplicates: {duplicate_filenames}.')
    logger.info(msg['message'])
    results = {'action': 'Uploaded',
               'resource': 'ImageResource',
               'message': msg,
               'images': images_ext
               }

    return results


@router.get("/images/untagged/", response_model=PResultsImageResource)
async def get_untagged_images(db: Session = Depends(get_db)):
    """
    get images with no plants assigned, yet
    """
    untagged_images = db.query(Image).filter(~Image.plants.any()).all()  # noqa
    images_ext = [_to_response_image(image) for image in untagged_images]

    logger.info(f'Returned {len(images_ext)} images.')
    results = {'ImagesCollection': images_ext,
               'message': get_message('Loaded images from backend.',
                                      description=f'Count: {len(images_ext)}')
               }
    return results


@router.put("/images/", response_model=PConfirmation)
async def update_images(modified_ext: PImageUpdated, db: Session = Depends(get_db)):
    """modify existing photo_file's metadata"""
    logger.info(f"Saving updates for {len(modified_ext.ImagesCollection)} images in db and exif tags.")
    for image_ext in modified_ext.ImagesCollection:
        # alter metadata in jpg exif tags
        logger.info(f'Updating {image_ext.filename}')
        PhotoMetadataAccessExifTags().save_photo_metadata(filename=image_ext.filename,
                                                          plant_names=[p.key for p in image_ext.plants],
                                                          keywords=[k.keyword for k in image_ext.keywords],
                                                          description=image_ext.description or '',
                                                          db=db)
        image = Image.get_image_by_filename(filename=image_ext.filename, db=db)
        # image = get_image_by_relative_path(relative_path=image_ext.relative_path, db=db, raise_exception=True)
        update_image_if_altered(image=image,
                                description=image_ext.description,
                                plant_ids=[plant.plant_id for plant in image_ext.plants],
                                keywords=[k.keyword for k in image_ext.keywords],
                                db=db)

    results = {'action': 'Saved',
               'resource': 'ImageResource',
               'message': get_message(f"Saved updates for {len(modified_ext.ImagesCollection)} images.")
               }

    return results


@router.post("/images/", response_model=PResultsImagesUploaded)
async def upload_images(request: Request, db: Session = Depends(get_db)):
    """upload new photo_file(s)
    todo: switch key in supplied plants list to id"""
    # the ui5 uploader control does somehow not work with the expected form/multipart format expected
    # via fastapi argument files = List[UploadFile] = File(...)
    # therefore, we directly go on the starlette request object
    form = await request.form()
    additional_data = json.loads(form.get('files-data'))
    # noinspection PyTypeChecker
    files: List[UploadFile] = form.getlist('files[]')

    # validate arguments manually as pydantic doesn't trigger here
    try:
        PImageUploadedMetadata(**additional_data)
    except ValidationError as err:
        throw_exception(str(err), request=request)

    # remove duplicates (filename already exists in file system)
    duplicate_filenames = remove_files_already_existing(files, RESIZE_SUFFIX)

    images: List[Image] = await save_image_files(files=files,
                                                 db=db,
                                                 plant_ids=additional_data['plants'],
                                                 keywords=additional_data['keywords'])
    images_ext = [_to_response_image(i) for i in images]

    msg = get_message(f'Saved {len(files)} images.' + (' Duplicates found.' if duplicate_filenames else ''),
                      message_type=PMessageType.WARNING if duplicate_filenames else PMessageType.INFORMATION,
                      description=f'Saved: {[p.filename for p in files]}.'
                                  f'\nSkipped Duplicates: {duplicate_filenames}.')
    logger.info(msg['message'])
    results = {'action': 'Uploaded',
               'resource': 'ImageResource',
               'message': msg,
               'images': images_ext
               }

    return results


@router.delete("/images/", response_model=PResultsImageDeleted)
async def delete_image(image_container: PImagesDelete, db: Session = Depends(get_db)):
    """move the file that should be deleted to another folder (not actually deleted, currently)"""
    for photo in image_container.images:
        # relative_path = get_relative_path(photo.absolute_path)
        # image = get_image_by_relative_path(relative_path=relative_path, db=db, raise_exception=True)
        image = Image.get_image_by_filename(filename=photo.filename, db=db)
        delete_image_file_and_db_entries(image=image, db=db)

    deleted = [image.filename for image in image_container.images]
    results = {'action': 'Deleted',
               'resource': 'ImageResource',
               'message': get_message(f'Deleted image(s)',
                                      description=f'Filenames: {deleted}')
               }
    return results


def _to_response_image(image: Image) -> PImage:
    k: ImageKeyword
    return PImage(
        filename=image.filename or '',
        keywords=[{'keyword': k.keyword} for k in image.keywords],
        plants=[PImagePlantTag(
            plant_id=p.id,
            key=p.plant_name,
            text=p.plant_name,
        ) for p in image.plants],
        description=image.description,
        record_date_time=image.record_date_time)


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


@router.post("/generate_missing_thumbnails", response_model=PMessage)
async def trigger_generate_missing_thumbnails(background_tasks: BackgroundTasks,
                                              db: Session = Depends(get_db)):
    """trigger the generation of missing thumbnails for occurrences"""
    msg = trigger_generation_of_missing_thumbnails(db=db, background_tasks=background_tasks)
    return get_message(msg)

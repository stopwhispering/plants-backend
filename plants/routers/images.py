from typing import List
import json
from sqlalchemy.orm import Session
import os
import logging
from pydantic.error_wrappers import ValidationError
from fastapi import UploadFile
from fastapi import APIRouter, Depends, Request

from plants.constants import RESIZE_SUFFIX
from plants.models.image_models import Image, get_image_by_relative_path, update_image_if_altered
from plants.services.image_services import save_image_files
from plants.services.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.util.ui_utils import MessageType, get_message, throw_exception
from plants.dependencies import get_db
from plants.models.plant_models import Plant
from plants.validation.image_validation import (PResultsImageResource, PImageUpdated, PImageUploadedMetadata, PImage,
                                                PPlantTag, PResultsImagesUploaded)
from plants import config
from plants.simple_services.image_services import remove_files_already_existing, get_relative_path
from plants.validation.event_validation import PImagesDelete
from plants.validation.image_validation import PResultsImageDeleted
from plants.validation.message_validation import PConfirmation

logger = logging.getLogger(__name__)

router = APIRouter(
        tags=["images"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/plants/{plant_id}/images/", response_model=List[PImage])
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
    # photo_files_ext = _get_pimages_from_photos(photos, db=db)
    images_ext = [_to_response_image(i) for i in images]

    msg = get_message(f'Saved {len(files)} images.' + (' Duplicates found.' if duplicate_filenames else ''),
                      message_type=MessageType.WARNING if duplicate_filenames else MessageType.INFORMATION,
                      description=f'Saved: {[p.filename for p in files]}.'
                                  f'\nSkipped Duplicates: {duplicate_filenames}.')
    logger.info(msg['message'])
    results = {'action':   'Uploaded',
               'resource': 'ImageResource',
               'message':  msg,
               'images':   images_ext
               }

    return results


@router.get("/images/untagged/", response_model=PResultsImageResource)
async def get_untagged_images(db: Session = Depends(get_db)):
    """
    get images with no plants assigned, yet
    """
    untagged_images = db.query(Image).filter(~Image.plants.any()).all()
    images_ext = [_to_response_image(image) for image in untagged_images]

    # # todooooo remove
    # images_ext = [i for i in images_ext if i.record_date_time]

    logger.info(f'Returned {len(images_ext)} images.')
    results = {'ImagesCollection': images_ext,
               'message':          get_message('Loaded images from backend.',
                                               description=f'Count: {len(images_ext)}')
               }
    return results


@router.put("/images/", response_model=PConfirmation)
async def update_images(request: Request, modified_ext: PImageUpdated, db: Session = Depends(get_db)):
    """modify existing photo_file's metadata"""
    logger.info(f"Saving updates for {len(modified_ext.ImagesCollection)} images in db and exif tags.")
    # with lock_photo_directory:
    for image_ext in modified_ext.ImagesCollection:
        # alter metadata in jpg exif tags
        logger.info(f'Updating {image_ext.absolute_path}')
        PhotoMetadataAccessExifTags().save_photo_metadata(absolute_path=image_ext.absolute_path,
                                                          plant_names=[p.key for p in image_ext.plants],
                                                          keywords=[k.keyword for k in image_ext.keywords],
                                                          description=image_ext.description or '')

        image = get_image_by_relative_path(relative_path=image_ext.relative_path, db=db, raise_exception=True)
        update_image_if_altered(image=image,
                                description=image_ext.description,
                                plant_ids=[plant.plant_id for plant in image_ext.plants],
                                keywords=[k.keyword for k in image_ext.keywords],
                                db=db)

    results = {'action':   'Saved',
               'resource': 'ImageResource',
               'message':  get_message(f"Saved updates for {len(modified_ext.ImagesCollection)} images.")
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
                      message_type=MessageType.WARNING if duplicate_filenames else MessageType.INFORMATION,
                      description=f'Saved: {[p.filename for p in files]}.'
                                  f'\nSkipped Duplicates: {duplicate_filenames}.')
    logger.info(msg['message'])
    results = {'action':   'Uploaded',
               'resource': 'ImageResource',
               'message':  msg,
               'images':   images_ext
               }

    return results


@router.delete("/images/", response_model=PResultsImageDeleted)
async def delete_image(request: Request, image_container: PImagesDelete, db: Session = Depends(get_db)):
    """move the file that should be deleted to another folder (not actually deleted, currently)"""

    # todo maybe replace loop
    for photo in image_container.images:

        old_path = photo.absolute_path
        if not old_path.is_file():
            logger.error(err_msg := f"File selected to be deleted not found: {old_path}")
            throw_exception(err_msg, request=request)

        new_path = config.path_deleted_photos.joinpath(old_path.name)

        try:
            os.replace(src=old_path,
                       dst=new_path)  # silently overwrites if privileges are sufficient
        except OSError as e:
            logger.error(err_msg := f'OSError when moving file {old_path} to {new_path}', exc_info=e)
            throw_exception(err_msg, description=f'Filename: {old_path.name}', request=request)
        logger.info(f'Moved file {old_path} to {new_path}')

        # todo remove from db
        # todo works for events, taxa, keywords, plants???
        # --> test
        relative_path = get_relative_path(photo.absolute_path)
        image = get_image_by_relative_path(relative_path=relative_path, db=db, raise_exception=True)
        db.delete(image)
        db.commit()

    deleted = [image.absolute_path.name for image in image_container.images]
    results = {'action':   'Deleted',
               'resource': 'ImageResource',
               'message':  get_message(f'Successfully deleted images',
                                       description=f'Filenames: {deleted}')
               }

    return results


def _to_response_image(image: Image) -> PImage:
    return PImage(
            relative_path=image.relative_path,
            relative_path_thumb=image.relative_path_thumb,
            keywords=[{'keyword': k.keyword} for k in image.keywords],
            plants=[PPlantTag(
                    plant_id=p.id,
                    key=p.plant_name,
                    text=p.plant_name,
                    ) for p in image.plants],
            description=image.description,
            filename=image.filename or '',
            absolute_path=image.absolute_path,
            record_date_time=image.record_date_time)

from typing import List, Tuple
import aiofiles
import json
from sqlalchemy.orm import Session
import os
import logging
from pydantic.error_wrappers import ValidationError
from fastapi import UploadFile
from fastapi import APIRouter, Depends, Request

from plants.util.ui_utils import MessageType, get_message, throw_exception
from plants.dependencies import get_db
from plants.models.plant_models import Plant
from plants.validation.image_validation import (PResultsImageResource, PImageUpdated, PImageUploadedMetadata, PImage,
                                                PKeyword, PPlantTag, PResultsImagesUploaded)
from plants import config
from plants.services.image_services import (resize_image, resizing_required, remove_files_already_existing)
from plants.services.PhotoDirectory import lock_photo_directory, get_photo_directory
from plants.services.Photo import Photo
from plants.util.filename_utils import with_suffix
from plants.validation.event_validation import PImagesDelete
from plants.validation.image_validation import PResultsImageDeleted
from plants.validation.message_validation import PConfirmation

RESIZE_SUFFIX = '_autoresized'

logger = logging.getLogger(__name__)

router = APIRouter(
        # prefix="/images",
        tags=["images"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/plants/{plant_id}/images/", response_model=List[PImage])
async def get_images_plant(plant_id: int, db: Session = Depends(get_db)):
    """
    get image information for requested plant_id from images and their exif tags including plants and keywords
    """
    # instantiate photo directory if required, get photos in external format from files exif data
    plant_name = Plant.get_plant_name_by_plant_id(plant_id, db=db, raise_exception=True)
    with lock_photo_directory:
        photo_files = get_photo_directory().get_photo_files(plant_name=plant_name)

    # if a plant_name is tagged for an image file but is not in the plants database, we set plant_id to None
    photo_files_ext = _get_pimages_from_photos(photo_files, db=db)

    # make_list_items_json_serializable(photo_files_ext)
    logger.info(f'Returned {len(photo_files_ext)} images for {plant_id} ({plant_name}).')
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

    plant_name = Plant.get_plant_name_by_plant_id(plant_id, db, raise_exception=True)

    # todo get rid of that key/text thing
    photos: List[Photo] = await _save_image_files(files=files,
                                                  request=request,
                                                  plants=({'key': plant_name, 'text': plant_name},)
                                                  )
    photo_files_ext = _get_pimages_from_photos(photos, db=db)

    msg = get_message(f'Saved {len(files)} images.' + (' Duplicates found.' if duplicate_filenames else ''),
                      message_type=MessageType.WARNING if duplicate_filenames else MessageType.INFORMATION,
                      description=f'Saved: {[p.filename for p in files]}.'
                                  f'\nSkipped Duplicates: {duplicate_filenames}.')
    logger.info(msg['message'])
    results = {'action':   'Uploaded',
               'resource': 'ImageResource',
               'message':  msg,
               'images': photo_files_ext
               }

    return results


@router.get("/images/", response_model=PResultsImageResource)
async def get_images(untagged: bool = False, db: Session = Depends(get_db)):
    """
    get image information for all plants from images and their exif tags including plants and keywords
    optionally, request only images that have no plants tagged, yet
    """
    # instantiate photo directory if required, get photos in external format from files exif data
    # with lock_photo_directory:
    #     photo_files_all = get_photo_directory().get_photo_files_ext()
    with lock_photo_directory:
        if untagged:
            photo_files_all = get_photo_directory().get_photo_files_untagged()
        else:
            photo_files_all = get_photo_directory().get_photo_files()

    photo_files_ext = _get_pimages_from_photos(photo_files_all, db=db)

    # filter out images whose only plants are configured to be inactive
    inactive_plants = set(p.plant_name for p in db.query(Plant.plant_name).filter_by(hide=True))
    photo_files_ext = [f for f in photo_files_ext if len(f.plants) != 1 or f.plants[0].key not in
                       inactive_plants]
    logger.debug(f'Filter out {len(photo_files_all) - len(photo_files_ext)} images due to Hide flag of the only tagged '
                 f'plant.')

    # make serializable
    # make_list_items_json_serializable(photo_files_ext)
    logger.info(f'Returned {len(photo_files_ext)} images.')
    results = {'ImagesCollection': photo_files_ext,
               'message':          get_message('Loaded images from backend.',
                                               description=f'Count: {len(photo_files_ext)}')
               }

    return results


@router.put("/images/", response_model=PConfirmation)
async def update_images(request: Request, modified_ext: PImageUpdated):
    """modify existing image's exif tags"""
    logger.info(f"Saving updates for {len(modified_ext.ImagesCollection)} images.")
    with lock_photo_directory:
        directory = get_photo_directory()
        for image_ext in modified_ext.ImagesCollection:
            if not (photo := directory.get_photo(image_ext.path_full_local)):
                throw_exception(f"Can't find image file: {image_ext.path_full_local}", request=request)

            logger.info(f'Updating changed image in PhotoDirectory Cache: {photo.path_full_local}')
            photo.tag_keywords = [k.keyword for k in image_ext.keywords]
            photo.tag_authors_plants = [p.key for p in image_ext.plants]
            photo.tag_description = image_ext.description
            photo.write_exif_tags()

    results = {'action':   'Saved',
               'resource': 'ImageResource',
               'message':  get_message(f"Saved updates for {len(modified_ext.ImagesCollection)} images.")
               }

    return results


@router.post("/images/", response_model=PResultsImagesUploaded)
async def upload_images(request: Request, db: Session = Depends(get_db)):
    """upload new image(s)
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

    # todo: get rid of that key/text/keyword dict
    plant_names = (Plant.get_plant_name_by_plant_id(p, db) for p in additional_data['plants'])
    plants = tuple({'key': p, 'text': p} for p in plant_names)  # if 'plants' in additional_data else []
    keywords = tuple({'keyword': k, 'text': k} for k in additional_data['keywords'])
    # if 'keywords' in additional_data else []

    # remove duplicates (filename already exists in file system)
    duplicate_filenames = remove_files_already_existing(files, RESIZE_SUFFIX)

    photos: List[Photo] = await _save_image_files(files=files,
                                                  request=request,
                                                  plants=plants,
                                                  keywords=keywords)
    photo_files_ext = _get_pimages_from_photos(photos, db=db)

    msg = get_message(f'Saved {len(files)} images.' + (' Duplicates found.' if duplicate_filenames else ''),
                      message_type=MessageType.WARNING if duplicate_filenames else MessageType.INFORMATION,
                      description=f'Saved: {[p.filename for p in files]}.'
                                  f'\nSkipped Duplicates: {duplicate_filenames}.')
    logger.info(msg['message'])
    results = {'action':   'Uploaded',
               'resource': 'ImageResource',
               'message':  msg,
               'images': photo_files_ext
               }

    return results


@router.delete("/images/", response_model=PResultsImageDeleted)
async def delete_image(request: Request, image_container: PImagesDelete):
    """move the file that should be deleted to another folder (not actually deleted, currently)"""

    # todo maybe replace loop
    for photo in image_container.images:

        old_path = photo.path_full_local
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

        # remove from PhotoDirectory cache
        with lock_photo_directory:
            photo_directory = get_photo_directory(instantiate=False)
            if photo_directory:
                photo_obj = photo_directory.get_photo(photo.path_full_local)
                photo_directory.remove_image_from_directory(photo_obj)

    deleted = [image.path_full_local.name for image in image_container.images]
    results = {'action':   'Deleted',
               'resource': 'ImageResource',
               'message':  get_message(f'Successfully deleted images',
                                       description=f'Filenames: {deleted}')
               }

    return results


async def _save_image_files(files: List[UploadFile],
                            request: Request,
                            plants: Tuple = (),
                            keywords: Tuple = (),
                            ) -> List[Photo]:
    """save the files supplied as starlette uploadfiles on os; assign plants and keywords"""
    photos = []
    for photo_upload in files:
        # save to file system
        path = config.path_original_photos_uploaded.joinpath(photo_upload.filename)
        logger.info(f'Saving {path}.')

        async with aiofiles.open(path, 'wb') as out_file:
            content = await photo_upload.read()  # async read
            await out_file.write(content)  # async write

        # photo_upload.save(path)  # we can't use object first and then save as this alters file object

        # resize file by lowering resolution if required
        if not config.resizing_size:
            pass
        elif not resizing_required(path, config.resizing_size):
            logger.info(f'No resizing required.')
        else:
            logger.info(f'Saving and resizing {path}.')
            resize_image(path=path,
                         save_to_path=with_suffix(path, RESIZE_SUFFIX),
                         size=config.resizing_size,
                         quality=config.jpg_quality)
            path = with_suffix(path, RESIZE_SUFFIX)

        # add to photo directory (cache) and add keywords and plant tags
        # (all the same for each uploaded photo)
        photo = Photo(path_full_local=path,
                      filename=path.name)
        photo.tag_authors_plants = [p['key'] for p in plants]
        photo.tag_keywords = [k['keyword'] for k in keywords]
        with lock_photo_directory:
            if p := get_photo_directory(instantiate=False):
                if p in p.photos:
                    throw_exception(f"Already found in PhotoDirectory cache: {photo.path_full_local}", request=request)
                p.photos.append(photo)

        # generate thumbnail image for frontend display and update file's exif tags
        photo.generate_thumbnails()
        photo.write_exif_tags()
        photos.append(photo)

    return photos


def _get_pimages_from_photos(photo_files: List[Photo], db: Session):
    """converts from internal Photo object to pydantic api structure"""
    photo_files_ext = [PImage(
            path_thumb=photo.path_thumb,
            path_original=photo.path_original,
            # keywords=[KeywordImageTagExt(keyword=k) for k in photo.tag_keywords],
            keywords=[PKeyword(keyword=k) for k in photo.tag_keywords],
            # plants=[PlantImageTagExt(
            plants=[PPlantTag(
                    plant_id=Plant.get_plant_id_by_plant_name(p, db=db, raise_exception=False),
                    key=p,
                    text=p,
                    ) for p in photo.tag_authors_plants],
            description='' if photo.tag_description.strip() == 'SONY DSC' else photo.tag_description,
            filename=photo.filename or '',
            path_full_local=photo.path_full_local,
            record_date_time=photo.record_date_time,
            ) for photo in photo_files]
    return photo_files_ext

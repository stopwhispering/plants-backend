from pathlib import Path
from typing import List, Sequence
import json
import logging
from pydantic.error_wrappers import ValidationError
from fastapi import UploadFile, BackgroundTasks
from fastapi import APIRouter, Depends, Request
from starlette.responses import FileResponse

from plants.modules.image.models import Image, ImageKeyword, ImageToPlantAssociation
from plants.modules.image.services import (
    save_image_files, delete_image_file_and_db_entries, trigger_generation_of_missing_thumbnails,
    fetch_images_for_plant, fetch_untagged_images,
    get_image_path_by_size, get_occurrence_thumbnail_path)
from plants.modules.image.photo_metadata_access_exif import PhotoMetadataAccessExifTags
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.message_services import throw_exception, get_message
from plants.dependencies import valid_plant, get_image_dal, get_taxon_dal, get_plant_dal
from plants.modules.image.schemas import (BResultsImageResource, BImageUpdated, FImageUploadedMetadata,
                                          BResultsImagesUploaded, ImageCreateUpdate, ImageRead)
from plants.modules.image.image_services_simple import remove_files_already_existing
from plants.modules.event.schemas import FImagesToDelete
from plants.modules.image.schemas import BResultsImageDeleted
from plants.shared.message_schemas import BSaveConfirmation, BConfirmation
from plants.shared.enums import FBMajorResource, BMessageType

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["images"],
    responses={404: {"description": "Not found"}},
)


@router.get("/plants/{plant_id}/images/", response_model=list[ImageRead])
async def get_images_for_plant(plant: Plant = Depends(valid_plant),
                               image_dal: ImageDAL = Depends(get_image_dal),
                               ):
    """
    get photo_file information for requested plant_id including (other) plants and keywords
    """
    images = await fetch_images_for_plant(plant, image_dal=image_dal)
    logger.info(f'Returned {len(images)} images for plant {plant.id}.')
    return images


@router.post("/plants/{plant_id}/images/", response_model=BResultsImagesUploaded)
async def upload_images_plant(request: Request,
                              plant: Plant = Depends(valid_plant),
                              image_dal: ImageDAL = Depends(get_image_dal),
                              plant_dal: PlantDAL = Depends(get_plant_dal)):
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
    duplicate_filenames, warnings = await remove_files_already_existing(files, image_dal=image_dal)

    images: list[ImageCreateUpdate] = await save_image_files(files=files,
                                                             image_dal=image_dal,
                                                             plant_dal=plant_dal,
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
async def get_untagged_images(image_dal: ImageDAL = Depends(get_image_dal)):
    """
    get images with no plants assigned, yet
    """
    untagged_images: list[ImageCreateUpdate] = await fetch_untagged_images(image_dal=image_dal)
    logger.info(msg := f'Returned {len(untagged_images)} images.')
    return {'action': 'Get untagged images',
            'ImagesCollection': untagged_images,
            'message': get_message(msg,
                                   description=f'Count: {len(untagged_images)}')
            }


@router.put("/images/", response_model=BSaveConfirmation)
async def update_images(modified_ext: BImageUpdated,
                        image_dal: ImageDAL = Depends(get_image_dal),
                        plant_dal: PlantDAL = Depends(get_plant_dal)):
    """
    modify existing photo_file's metadata
    """
    logger.info(f"Saving updates for {len(modified_ext.ImagesCollection)} images in db and exif tags.")
    for image_ext in modified_ext.ImagesCollection:
        # alter metadata in jpg exif tags
        logger.info(f'Updating {image_ext.filename}')
        await PhotoMetadataAccessExifTags().save_photo_metadata(image_id=image_ext.id,
                                                                plant_names=[p.plant_name for p in image_ext.plants],
                                                                keywords=[k.keyword for k in image_ext.keywords],
                                                                description=image_ext.description or '',
                                                                image_dal=image_dal)
        # image = Image.get_image_by_filename(filename=image_ext.filename, db=db)
        image = await image_dal.get_image_by_filename(filename=image_ext.filename)
        await _update_image_if_altered(image=image,
                                       description=image_ext.description,
                                       plant_ids=[plant.plant_id for plant in image_ext.plants],
                                       keywords=[k.keyword for k in image_ext.keywords],
                                       plant_dal=plant_dal,
                                       image_dal=image_dal)

    return {'resource': FBMajorResource.IMAGE,
            'message': get_message(f"Saved updates for {len(modified_ext.ImagesCollection)} images.")
            }


@router.post("/images/", response_model=BResultsImagesUploaded)
async def upload_images(request: Request,
                        image_dal: ImageDAL = Depends(get_image_dal),
                        plant_dal: PlantDAL = Depends(get_plant_dal)
                        ):
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
    duplicate_filenames, warnings = await remove_files_already_existing(files, image_dal=image_dal)

    images: list[ImageCreateUpdate] = await save_image_files(files=files,
                                                             image_dal=image_dal,
                                                             plant_dal=plant_dal,
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
async def delete_image(image_container: FImagesToDelete, image_dal: ImageDAL = Depends(get_image_dal)):
    """move the file that should be deleted to another folder (not actually deleted, currently)"""
    for image_to_delete in image_container.images:
        image = await image_dal.by_id(image_id=image_to_delete.id)
        if image.filename != image_to_delete.filename:
            logger.error(err_msg := f'Image {image.id} has unexpected filename: {image.filename}. '
                                    f'Expected filename: {image_to_delete.filename}. Analyze this inconsistency!')
            throw_exception(err_msg)

        await delete_image_file_and_db_entries(image=image, image_dal=image_dal)

    deleted_files = [image.filename for image in image_container.images]
    return {
        'action': 'Deleted',
        'message': get_message(f'Deleted {len(image_container.images)} image(s)',
                               description=f'Filenames: {deleted_files}')
    }


@router.get("/occurrence_thumbnail",
            # Prevent FastAPI from adding "application/json" as an additional
            # response media type in the autogenerated OpenAPI specification.
            response_class=FileResponse)
async def get_occurrence_thumbnail(gbif_id: int,
                                   occurrence_id: int,
                                   img_no: int,
                                   taxon_dal: TaxonDAL = Depends(get_taxon_dal)):
    path: Path = await get_occurrence_thumbnail_path(gbif_id=gbif_id,
                                                     occurrence_id=occurrence_id,
                                                     img_no=img_no,
                                                     taxon_dal=taxon_dal)

    # media_type here sets the media type of the actual response sent to the client.
    return FileResponse(path=path, media_type="image/jpeg", filename=path.name)


@router.get("/photo", response_class=FileResponse)
async def get_photo(filename: str, width: int = None, height: int = None, image_dal: ImageDAL = Depends(get_image_dal)):
    image_path = await get_image_path_by_size(filename=filename,
                                              width=width,
                                              height=height,
                                              image_dal=image_dal)

    # media_type here sets the media type of the actual response sent to the client.
    return FileResponse(path=image_path, media_type="image/jpeg", filename=image_path.name)


@router.post("/generate_missing_thumbnails", response_model=BConfirmation)
async def trigger_generate_missing_thumbnails(background_tasks: BackgroundTasks,
                                              image_dal: ImageDAL = Depends(get_image_dal)):
    """trigger the generation of missing thumbnails for occurrences"""
    msg = await trigger_generation_of_missing_thumbnails(image_dal=image_dal, background_tasks=background_tasks)
    return {
        'action': 'Triggering generation of missing thumbnails',
        'message': get_message(msg)
    }


async def _update_image_if_altered(image: Image,
                                   description: str,
                                   plant_ids: Sequence[int],
                                   keywords: Sequence[str],
                                   plant_dal: PlantDAL,
                                   image_dal: ImageDAL
                                   ):
    """compare current database record for image with supplied field values; update db entry if different;
    Note: record_date_time is only set at upload, so we're not comparing or updating it."""
    # description
    if description != image.description and not (not description and not image.description):
        image.description = description

    # plants
    new_plants = set([await plant_dal.by_id(plant_id) for plant_id in plant_ids])
    removed_image_to_plant_associations = [a for a in image.image_to_plant_associations
                                           if a.plant not in new_plants]
    added_image_to_plant_associations = [ImageToPlantAssociation(
        image=image,
        plant=p, )
        for p in new_plants if p not in image.plants]
    for removed_image_to_plant_association in removed_image_to_plant_associations:
        await plant_dal.delete_image_to_plant_association(removed_image_to_plant_association)
    if added_image_to_plant_associations:
        image.image_to_plant_associations.extend(added_image_to_plant_associations)

    # keywords
    current_keywords = set(k.keyword for k in image.keywords)
    removed_keywords = [k for k in image.keywords if k.keyword not in keywords]
    added_keywords = [ImageKeyword(image_id=image.id,
                                   keyword=k)
                      for k in set(keywords) if k not in current_keywords]

    if removed_keywords:
        await image_dal.delete_keywords_from_image(image, removed_keywords)
    if added_keywords:
        await image_dal.create_new_keywords_for_image(image, added_keywords)

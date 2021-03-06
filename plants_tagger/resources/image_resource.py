from flask_restful import Resource
from flask import request
import os
import json
import logging
from flask_2_ui5_py import MessageType, get_message, throw_exception, make_list_items_json_serializable
from pydantic.error_wrappers import ValidationError

from plants_tagger.config_local import PATH_DELETED_PHOTOS
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.plant_models import Plant
from plants_tagger.validation.image_validation import (PResultsImageResource, PImageUpdated, PImageUploadedMetadata,
                                                       PImage, PResultsImageDeleted)
from plants_tagger.validation.message_validation import PConfirmation
from plants_tagger.services.os_paths import PATH_ORIGINAL_PHOTOS_UPLOADED
from plants_tagger import config
from plants_tagger.services.image_services import (resize_image, resizing_required, remove_files_already_existing)
from plants_tagger.services.PhotoDirectory import lock_photo_directory, get_photo_directory
from plants_tagger.services.Photo import Photo
from plants_tagger.util.filename_utils import with_suffix

logger = logging.getLogger(__name__)
RESIZE_SUFFIX = '_autoresized'


class ImageResource(Resource):
    @staticmethod
    def get():
        """
        get image information from images and their exif tags including plants and keywords
        """
        # instantiate photo directory if required, get photos in external format from files exif data
        with lock_photo_directory:
            photo_files_all = get_photo_directory().get_photo_files_ext()

        # filter out images whose only plants are configured to be inactive
        inactive_plants = set(p.plant_name for p in get_sql_session().query(Plant.plant_name).filter_by(hide=True))
        photo_files = [f for f in photo_files_all if len(f['plants']) != 1 or f['plants'][0]['key'] not in
                       inactive_plants]
        logger.debug(f'Filter out {len(photo_files_all) - len(photo_files)} images due to Hide flag of the only tagged '
                     f'plant.')

        # make serializable anad validate
        make_list_items_json_serializable(photo_files)
        logger.info(f'Returned {len(photo_files)} images.')
        results = {'ImagesCollection': photo_files,
                   'message': get_message('Loaded images from backend.',
                                          description=f'Count: {len(photo_files)}')
                   }
        try:
            PResultsImageResource(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def put(**kwargs):
        """modify existing image's exif tags"""
        if not kwargs:
            kwargs = request.get_json(force=True)

        # evaluate arguments
        try:
            modified_ext = PImageUpdated(**kwargs)
        except ValidationError as err:
            modified_ext = None
            throw_exception(str(err))

        logger.info(f"Saving updates for {len(modified_ext.ImagesCollection)} images.")
        with lock_photo_directory:
            directory = get_photo_directory()
            for image_ext in modified_ext.ImagesCollection:
                if not (photo := directory.get_photo(image_ext.path_full_local)):
                    throw_exception(f"Can't find image file: {image_ext.path_full_local}")

                logger.info(f'Updating changed image in PhotoDirectory Cache: {photo.path_full_local}')
                photo.tag_keywords = [k.keyword for k in image_ext.keywords]
                photo.tag_authors_plants = [p.key for p in image_ext.plants]
                photo.tag_description = image_ext.description
                photo.write_exif_tags()

        results = {'action':   'Saved',
                   'resource': 'ImageResource',
                   'message':  get_message(f"Saved updates for {len(kwargs['ImagesCollection'])} images.")
                   }

        # evaluate output
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def post():
        """upload new image(s)"""
        # check if any of the files already exists locally
        files = request.files.getlist('photoUpload[]')
        additional_data = json.loads(request.form['photoUpload-data']) if request.form['photoUpload-data'] else {}

        # evaluate arguments
        try:
            PImageUploadedMetadata(**additional_data)
        except ValidationError as err:
            throw_exception(str(err))

        plants = [{'key': p, 'text': p} for p in additional_data['plants']] if 'plants' in additional_data else []
        keywords = [{'keyword': k, 'text': k} for k in additional_data['keywords']] \
            if 'keywords' in additional_data else []

        # remove duplicates (filename already exists in file system)
        duplicate_filenames = remove_files_already_existing(files, RESIZE_SUFFIX)

        for photo_upload in files:
            # save to file system
            path = os.path.join(PATH_ORIGINAL_PHOTOS_UPLOADED, photo_upload.filename)
            logger.info(f'Saving {path}.')
            photo_upload.save(path)  # we can't use object first and then save as this alters file object

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
                             quality=config.quality)
                path = with_suffix(path, RESIZE_SUFFIX)

            # add to photo directory (cache) and add keywords and plant tags
            # (all the same for each uploaded photo)
            photo = Photo(path_full_local=path,
                          filename=os.path.basename(path))
            photo.tag_authors_plants = [p['key'] for p in plants]
            photo.tag_keywords = [k['keyword'] for k in keywords]
            with lock_photo_directory:
                if p := get_photo_directory(instantiate=False):
                    if p in p.photos:
                        throw_exception(f"Already found in PhotoDirectory cache: {photo.path_full_local}")
                    p.photos.append(photo)

            # generate thumbnail image for frontend display and update file's exif tags
            photo.generate_thumbnails()
            photo.write_exif_tags()

        msg = get_message(f'Saved {len(files)} images.' + (' Duplicates found.' if duplicate_filenames else ''),
                          message_type=MessageType.WARNING if duplicate_filenames else MessageType.INFORMATION,
                          description=f'Saved: {[p.filename for p in files]}.'
                                      f'\nSkipped Duplicates: {duplicate_filenames}.')
        logger.info(msg['message'])
        results = {'action':   'Uploaded',
                   'resource': 'ImageResource',
                   'message':  msg
                   }

        # evaluate output
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def delete():
        """move the file that should be deleted to another folder (not actually deleted, currently)"""
        photo = request.get_json()

        # evaluate arguments
        try:
            PImage(**photo)
        except ValidationError as err:
            throw_exception(str(err))

        old_path = photo['path_full_local']
        if not os.path.isfile(old_path):
            logger.error(err_msg := f"File selected to be deleted not found: {old_path}")
            throw_exception(err_msg)

        filename = os.path.basename(old_path)
        new_path = os.path.join(PATH_DELETED_PHOTOS, filename)

        try:
            os.replace(src=old_path,
                       dst=new_path)  # silently overwrites if privileges are sufficient
        except OSError as e:
            logger.error(err_msg := f'OSError when moving file {old_path} to {new_path}', exc_info=e)
            throw_exception(err_msg, description=f'Filename: {os.path.basename(old_path)}')
        logger.info(f'Moved file {old_path} to {new_path}')

        # remove from PhotoDirectory cache
        with lock_photo_directory:
            photo_directory = get_photo_directory(instantiate=False)
            if photo_directory:
                photo_obj = photo_directory.get_photo(photo['path_full_local'])
                photo_directory.remove_image_from_directory(photo_obj)

        results = {'action':   'Deleted',
                   'resource': 'ImageResource',
                   'message':  get_message(f'Successfully deleted image',
                                           description=f'Filename: {os.path.basename(old_path)}'),
                   'photo':    photo}

        # evaluate output
        try:
            PResultsImageDeleted(**results)
        except ValidationError as err:
            throw_exception(str(err))

        # send the photo back to frontend; it will be removed from json model there
        return results, 200

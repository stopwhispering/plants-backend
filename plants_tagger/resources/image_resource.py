from flask_restful import Resource
from flask import request
import os
import logging

import plants_tagger.models.files
# from plants_tagger.models.files import photo_directory
from plants_tagger.config_local import path_uploaded_photos_original, path_frontend_temp, path_deleted_photos
from plants_tagger.models.files import lock_photo_directory

logger = logging.getLogger(__name__)


# called ImageResource without 2 for historical reasons
# currently only used for uploading images
# todo: merge with other images resource
class ImageResource(Resource):
    @staticmethod
    def post():
        # check if any of the files already exists locally
        files = request.files.getlist('photoUpload[]')

        # import sys
        # print(sys.getsizeof(request.data))

        for photo_upload in files:
            path = os.path.join(path_uploaded_photos_original, photo_upload.filename)
            logger.debug(f'Checking uploaded photo ({photo_upload.mimetype}) to be saved as {path}.')
            if os.path.isfile(path):  # todo: better check in all folders!
                logger.error(f'Canceled file upload (duplicate): {photo_upload.filename}')
                return {'error': f'File already uploaded: {photo_upload.filename}'}, 500

        # save only if there's no duplicate among uploaded files
        for photo_upload in files:
            path = os.path.join(path_uploaded_photos_original, photo_upload.filename)
            logger.info(f'Saving {path}.')
            photo_upload.save(path)

        # trigger re-reading exif tags (only required if already instantiated, otherwise data is re-read anyway)
        # todo: only read new files exif-tags; only implement if there are problems with lots of images (curr. not)
        if plants_tagger.models.files.photo_directory:
            plants_tagger.models.files.photo_directory.refresh_directory(path_frontend_temp)
        else:
            logger.warning('No instantiated photo directory found.')

        logger.info(f'Successfully saved {len(files)} images.')
        return {'success': f'Successfully saved {len(files)} images.'}, 200

    @staticmethod
    def delete():
        """move the file that should be deleted to another folder (not actually deleted"""
        photo = request.get_json()
        old_path = photo['path_full_local']
        if not os.path.isfile(old_path):
            return {'error': 'File not found'}, 500

        filename = os.path.basename(old_path)
        new_path = os.path.join(path_deleted_photos, filename)

        try:
            os.replace(src=old_path,
                       dst=new_path)  # silently overwrites if privileges are sufficient
        except OSError as e:
            logger.error(f'OSError when moving file {old_path} to {new_path}', exc_info=e)
            return {'error': f'OSError when moving file {old_path} to {new_path}'}, 500
        logger.info(f'Moved file {old_path} to {new_path}')

        # remove from PhotoDirectory cache
        with lock_photo_directory:
            if plants_tagger.models.files.photo_directory:
                plants_tagger.models.files.photo_directory.remove_image_from_directory(photo)

        # send the photo back to frontend; it will be removed from json model there
        return {'success': f'Successfully deleted image {os.path.basename(old_path)}',
                'photo': photo}, 200

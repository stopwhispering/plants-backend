from flask_restful import Resource
from flask import request
import os
import logging

from plants_tagger.config import path_uploaded_photos_original

logger = logging.getLogger(__name__)


# called ImageResource without 2 for historical reasons
# currently only used for uploading images
# todo: merge with other images resource
class ImageResource(Resource):
    @staticmethod
    def post():
        # check if any of the files already exists locally
        files = request.files.getlist('photoUpload[]')
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

        logger.info(f'Successfully saved {len(files)} images.')
        return {'success': f'Successfully saved {len(files)} images.'}, 200

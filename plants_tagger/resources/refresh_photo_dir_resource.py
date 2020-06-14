import logging
from datetime import datetime
from flask_restful import Resource
import pickle
from flask_2_ui5_py import get_message

import plants_tagger.config_local
from plants_tagger.services.os_paths import PATH_ORIGINAL_PHOTOS
from plants_tagger.services.image_services import lock_photo_directory
from plants_tagger.services.PhotoDirectory import PhotoDirectory
from plants_tagger.services import image_services

logger = logging.getLogger(__name__)


class RefreshPhotoDirectoryResource(Resource):
    @staticmethod
    def post():
        """recreates the photo directory, i.e. re-reads directory, creates missing thumbnails etc."""
        with lock_photo_directory:
            if not image_services.photo_directory:
                image_services.photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
            image_services.photo_directory.refresh_directory(plants_tagger.config_local.PATH_BASE)

        # upon manually refreshing image data, we pickle the image tags directory
        filename = 'photodir_' + datetime.now().strftime("%Y%m%d_%H%M%S") + '.pickle'
        pickle.dump(image_services.photo_directory, open(filename, "wb"))

        logger.info(f'Refreshed photo directory')
        return {'message':  get_message(f'Refreshed photo directory')
                }, 200

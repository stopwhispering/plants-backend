import logging
from datetime import datetime

from flask_restful import Resource
import pickle
from flask_2_ui5_py import get_message

import plants_tagger.config_local
from plants_tagger.models.os_paths import PATH_ORIGINAL_PHOTOS
from plants_tagger.models.files import lock_photo_directory, PhotoDirectory
from plants_tagger.models import files

logger = logging.getLogger(__name__)


class RefreshPhotoDirectoryResource(Resource):
    @staticmethod
    def post():
        """recreates the photo directory, i.e. re-reads directory, creates missing thumbnails etc."""
        with lock_photo_directory:
            if not files.photo_directory:
                files.photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
            files.photo_directory.refresh_directory(plants_tagger.config_local.PATH_BASE)

        # upon manually refreshing image data, we pickle the image tags directory
        filename = 'photodir_' + datetime.now().strftime("%Y%m%d_%H%M%S") + '.pickle'
        pickle.dump(files.photo_directory, open(filename, "wb"))

        logger.info(f'Refreshed photo directory')
        return {'message':  get_message(f'Refreshed photo directory')
                }, 200

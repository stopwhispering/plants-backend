import logging
from flask_restful import Resource

import plants_tagger.config_local
from plants_tagger.models.os_paths import PATH_ORIGINAL_PHOTOS
from plants_tagger.models.files import lock_photo_directory, PhotoDirectory
from flask_2_ui5_py import get_message
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

        logger.info(f'Refreshed photo directory')
        return {'message':  get_message(f'Refreshed photo directory')
                }, 200

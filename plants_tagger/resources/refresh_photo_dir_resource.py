import logging
from flask_restful import Resource
from flask_2_ui5_py import get_message, throw_exception
from pydantic.error_wrappers import ValidationError

from plants_tagger.validation.message_validation import PConfirmation
from plants_tagger.services.PhotoDirectory import lock_photo_directory, get_photo_directory

logger = logging.getLogger(__name__)


class RefreshPhotoDirectoryResource(Resource):
    @staticmethod
    def post():
        """recreates the photo directory, i.e. re-reads directory, creates missing thumbnails etc."""
        with lock_photo_directory:
            get_photo_directory().refresh_directory()

        logger.info(message := f'Refreshed photo directory')
        results = {'action':   'Function refresh Photo Directory',
                   'resource': 'RefreshPhotoDirectoryResource',
                   'message':  get_message(message)}

        # evaluate output
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

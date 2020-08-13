import logging
from flask_restful import Resource
from flask_2_ui5_py import get_message

from plants_tagger.services.PhotoDirectory import lock_photo_directory, get_photo_directory

logger = logging.getLogger(__name__)


class RefreshPhotoDirectoryResource(Resource):
    @staticmethod
    def post():
        """recreates the photo directory, i.e. re-reads directory, creates missing thumbnails etc."""
        with lock_photo_directory:
            # if not photo_directory:
            #     plants_tagger.services.PhotoDirectory.photo_directory = PhotoDirectory()
            get_photo_directory().refresh_directory()

        # # upon manually refreshing image data, we pickle the image tags directory
        # filename = 'photodir_' + datetime.now().strftime("%Y%m%d_%H%M%S") + '.pickle'
        # pickle.dump(image_services.photo_directory, open(filename, "wb"))

        logger.info(f'Refreshed photo directory')
        return {'message':  get_message(f'Refreshed photo directory')
                }, 200

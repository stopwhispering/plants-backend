from flask_restful import Resource
from flask import request

import plants_tagger.config_local
from plants_tagger.models.os_paths import PATH_ORIGINAL_PHOTOS
from plants_tagger.models.files import lock_photo_directory, PhotoDirectory
from plants_tagger.util.util import parse_resource_from_request
from plants_tagger.models import files


class RefreshPhotoDirectoryResource(Resource):
    @staticmethod
    def post():
        """recreates the photo directory, i.e. re-reads directory, creates missing thumbnails etc."""
        with lock_photo_directory:
            if not files.photo_directory:
                files.photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
            files.photo_directory.refresh_directory(plants_tagger.config_local.PATH_BASE)
        return {'message':  {
                            'type':           'Information',
                            'message':        f'Refreshed photo directory',
                            'additionalText': None,
                            'description':    f'Resource: {parse_resource_from_request(request)}'
                            }
                }, 200

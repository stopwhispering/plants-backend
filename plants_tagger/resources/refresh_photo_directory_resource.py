from flask_restful import Resource
from flask import request

import plants_tagger.config_local
from plants_tagger.models.files import photo_directory, lock_photo_directory, PhotoDirectory, FOLDER_ROOT


# todo: implement api for this (button )
from plants_tagger.util.util import parse_resource_from_request


class RefreshPhotoDirectoryResource(Resource):
    @staticmethod
    def post():
        """recreates the photo directory, i.e. re-reads directory, creates missing thumbnails etc."""
        with lock_photo_directory:
            global photo_directory
            if not photo_directory:
                photo_directory = PhotoDirectory(FOLDER_ROOT)
            photo_directory.refresh_directory(plants_tagger.config_local.path_frontend_temp)
        # return {'success': 'Refreshed photo directory.'}  # todo return image list ?
        return {'message':  {
            'type':           'Information',
            'message':        f'Refreshed photo directory',
            'additionalText': None,
            'description':    f'Resource: {parse_resource_from_request(request)}'
            }
               }, 200

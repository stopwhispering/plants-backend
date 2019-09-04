from flask_restful import Resource
from flask import request
import os
import json
import logging

import plants_tagger.models.files
# from plants_tagger.models.files import photo_directory
from plants_tagger.config_local import path_uploaded_photos_original, path_frontend_temp, path_deleted_photos
from plants_tagger.models.files import lock_photo_directory, read_exif_tags, write_new_exif_tags, get_plants_data
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)


class ImageResource(Resource):
    @staticmethod
    def post():
        # check if any of the files already exists locally
        files = request.files.getlist('photoUpload[]')
        # plants_raw = json.loads(request.form['photoUpload-data']) if request.form['photoUpload-data'] else []
        # plants = [{'key': p, 'text': p} for p in plants_raw]

        additional_data = json.loads(request.form['photoUpload-data']) if request.form['photoUpload-data'] else {}
        if 'plants' in additional_data:
            plants = [{'key': p, 'text': p} for p in additional_data['plants']]
        else:
            plants = []

        if 'keywords' in additional_data:
            keywords = [{'key': k, 'text': k} for k in additional_data['keywords']]
        else:
            keywords = []

        # remove duplicates (already saved)
        duplicate_filenames = []
        for i, photo_upload in enumerate(files[:]):  # need to loop on copy if we want to delete within loop
            path = os.path.join(path_uploaded_photos_original, photo_upload.filename)
            logger.debug(f'Checking uploaded photo ({photo_upload.mimetype}) to be saved as {path}.')
            if os.path.isfile(path):  # todo: better check in all folders!
                duplicate_filenames.append(photo_upload.filename)
                files.pop(i)
                logger.warning(f'Skipping file upload (duplicate) for: {photo_upload.filename}')
                # return {'error': f'File already uploaded: {photo_upload.filename}'}, 500

        if files:
            for photo_upload in files:
                path = os.path.join(path_uploaded_photos_original, photo_upload.filename)
                logger.info(f'Saving {path}.')
                photo_upload.save(path)

                # add tagged plants (update/create exif tags)
                if plants or keywords:
                    image_metadata = {'path_full_local': path}
                    read_exif_tags(image_metadata)
                    plants_data = get_plants_data([image_metadata])
                    if plants:
                        logger.info(f'Tagging new image with plants: {additional_data["plants"]}')
                        plants_data[0]['plants'] = plants
                    if keywords:
                        logger.info(f'Tagging new image with keywords: {additional_data["keywords"]}')
                        plants_data[0]['keywords'] = keywords
                    write_new_exif_tags(plants_data, temp=True)

            # trigger re-reading exif tags (only required if already instantiated, otherwise data is re-read anyway)
            # todo: only read new files exif-tags; only implement if there are problems with lots of images (curr. not)
            if plants_tagger.models.files.photo_directory:
                plants_tagger.models.files.photo_directory.refresh_directory(path_frontend_temp)
            else:
                logger.warning('No instantiated photo directory found.')

        if files and not duplicate_filenames:
            msg_type = 'Information'
            msg_message = f'Successfully saved {len(files)} images.'
            msg_additional_text = None
        else:
            msg_type = 'Warning'
            msg_message = f'Duplicates found when saving.'
            msg_additional_text = 'Saved {[p.filename for p in files]}.\nSkipped {duplicate_filenames}.'

        logger.info(msg_message)
        return {'message':  {
                    'type':           msg_type,
                    'message':        msg_message,
                    'additionalText': msg_additional_text,
                    'description':    f'Resource: {parse_resource_from_request(request)}',
                    }
                }, 200

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
            # return {'error': f'OSError when moving file {old_path} to {new_path}'}, 500
            return({'message': {
                            'type': 'Error',
                            'message': f'OSError when moving file {old_path} to {new_path}',
                            'additionalText': None,
                            'description': f'Filename: {os.path.basename(old_path)}\nResource:'
                                           f' {parse_resource_from_request(request)}'
                            }}), 500
        logger.info(f'Moved file {old_path} to {new_path}')

        # remove from PhotoDirectory cache
        with lock_photo_directory:
            if plants_tagger.models.files.photo_directory:
                plants_tagger.models.files.photo_directory.remove_image_from_directory(photo)

        # send the photo back to frontend; it will be removed from json model there
        # return {'success': f'Successfully deleted image {os.path.basename(old_path)}', 'photo': photo}, 200
        return {'message': {
                            'type': 'Information',
                            'message': f'Successfully deleted image',
                            'additionalText': None,
                            'description': f'Filename: {os.path.basename(old_path)}\nResource:'
                                           f' {parse_resource_from_request(request)}'
                            },
                'photo': photo}, 200

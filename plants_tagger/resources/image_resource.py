from flask_restful import Resource
from flask import request
import os
import json
import logging

import plants_tagger.models.files
# from plants_tagger.models.files import photo_directory
from plants_tagger.config_local import PATH_BASE, PATH_DELETED_PHOTOS
from plants_tagger.models.os_paths import PATH_ORIGINAL_PHOTOS_UPLOADED
from plants_tagger.models.files import lock_photo_directory, read_exif_tags, write_new_exif_tags, get_plants_data
from plants_tagger.util.json_helper import MessageType, get_message, throw_exception

logger = logging.getLogger(__name__)


class ImageResource(Resource):
    @staticmethod
    def post():
        # check if any of the files already exists locally
        files = request.files.getlist('photoUpload[]')
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
            path = os.path.join(PATH_ORIGINAL_PHOTOS_UPLOADED, photo_upload.filename)
            logger.debug(f'Checking uploaded photo ({photo_upload.mimetype}) to be saved as {path}.')
            if os.path.isfile(path):  # todo: better check in all folders!
                duplicate_filenames.append(photo_upload.filename)
                files.pop(i)
                logger.warning(f'Skipping file upload (duplicate) for: {photo_upload.filename}')

        if files:
            for photo_upload in files:
                path = os.path.join(PATH_ORIGINAL_PHOTOS_UPLOADED, photo_upload.filename)
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
                    write_new_exif_tags(plants_data)

            # trigger re-reading exif tags (only required if already instantiated, otherwise data is re-read anyway)
            if plants_tagger.models.files.photo_directory:
                plants_tagger.models.files.photo_directory.refresh_directory(PATH_BASE)
            else:
                logger.warning('No instantiated photo directory found.')

        if files and not duplicate_filenames:
            msg = get_message(f'Successfully saved {len(files)} images.')
        else:
            msg = get_message(f'Duplicates found when saving.',
                              message_type=MessageType.WARNING,
                              additional_text='click for details',
                              description=f'Saved {[p.filename for p in files]}.'
                                          f'\nSkipped {duplicate_filenames}.')

        logger.info(msg['message'])
        return {'message':  msg}, 200

    @staticmethod
    def delete():
        """move the file that should be deleted to another folder (not actually deleted"""
        photo = request.get_json()
        old_path = photo['path_full_local']
        if not os.path.isfile(old_path):
            logger.error(f"File selected to be deleted not found: {old_path}")
            throw_exception(f"File selected to be deleted not found: {old_path}")

        filename = os.path.basename(old_path)
        new_path = os.path.join(PATH_DELETED_PHOTOS, filename)

        try:
            os.replace(src=old_path,
                       dst=new_path)  # silently overwrites if privileges are sufficient
        except OSError as e:
            logger.error(f'OSError when moving file {old_path} to {new_path}', exc_info=e)
            throw_exception(f'OSError when moving file {old_path} to {new_path}',
                            description=f'Filename: {os.path.basename(old_path)}')
        logger.info(f'Moved file {old_path} to {new_path}')

        # remove from PhotoDirectory cache
        with lock_photo_directory:
            if plants_tagger.models.files.photo_directory:
                plants_tagger.models.files.photo_directory.remove_image_from_directory(photo)

        # send the photo back to frontend; it will be removed from json model there
        return {'message': get_message(f'Successfully deleted image',
                                       description=f'Filename: {os.path.basename(old_path)}'),
                'photo': photo}, 200

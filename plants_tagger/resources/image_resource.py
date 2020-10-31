from flask_restful import Resource
from flask import request
import os
import json
import logging

from flask_2_ui5_py import MessageType, get_message, throw_exception, make_list_items_json_serializable
from pydantic.error_wrappers import ValidationError

from plants_tagger.config_local import PATH_BASE, PATH_DELETED_PHOTOS
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.models.plant_models import Plant
from plants_tagger.models.validation.image_validation import PResultsImageResource, PImageUpdated, \
    PImageUploadedMetadata, PImage, PResultsImageDeleted
from plants_tagger.models.validation.message_validation import PConfirmation
from plants_tagger.services.os_paths import PATH_ORIGINAL_PHOTOS_UPLOADED
from plants_tagger import config
from plants_tagger.services.image_services import get_plants_data, \
    resize_image, resizing_required, get_exif_tags_for_folder
from plants_tagger.services.PhotoDirectory import lock_photo_directory, get_photo_directory
from plants_tagger.services.exif_services import write_new_exif_tags
from plants_tagger.util.exif_utils import read_exif_tags
from plants_tagger.util.filename_utils import with_suffix

logger = logging.getLogger(__name__)
RESIZE_SUFFIX = '_autoresized'


class ImageResource(Resource):
    @staticmethod
    def get():
        """read image information from images and their exif tags"""
        files_data, _ = get_exif_tags_for_folder()
        i = len(files_data)

        # get plants whose images are configured to be hidden (hide-flag is set in plants table, i.e. deleted in
        # web frontend)
        plants_to_hide = get_sql_session().query(Plant).filter_by(hide=True).all()
        plants_to_hide_names = [p.plant_name for p in plants_to_hide]
        logger.debug(f'Hiding images that have only hidden plants tagged: {plants_to_hide_names}')
        files_data = [f for f in files_data if not (len(f['plants']) == 1 and f['plants'][0] in plants_to_hide_names)]
        logger.debug(f'Filter out {i - len(files_data)} images due to Hide flag of the only tagged plant.')

        for image in files_data:
            if image['plants']:
                image['plants'] = [{'key': p, 'text': p} for p in image['plants']]
            if image['keywords']:
                image['keywords'] = [{'keyword': p} for p in image['keywords']]

            # get rid of annoying camera default image description
            if image.get('description').strip() == 'SONY DSC':
                image['description'] = ''

        make_list_items_json_serializable(files_data)
        logger.info(f'Returned {len(files_data)} images.')
        results = {'ImagesCollection': files_data,
                   'message':          get_message('Loaded images from backend.',
                                                   description=f'Count: {len(files_data)}')
                   }
        # valitdate
        try:
            PResultsImageResource(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def put(**kwargs):
        """modify existing image's exif tags"""
        if not kwargs:
            kwargs = request.get_json(force=True)

        # evaluate input
        try:
            PImageUpdated(**kwargs)
        except ValidationError as err:
            throw_exception(str(err))

        logger.info(f"Saving updates for {len(kwargs['ImagesCollection'])} images.")
        write_new_exif_tags(kwargs['ImagesCollection'])

        results = {'action':   'Saved',
                   'resource': 'ImageResource',
                   'message':  get_message(f"Saved updates for {len(kwargs['ImagesCollection'])} images.")
                   }

        # evaluate output
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def post():
        """upload new image(s)"""
        # check if any of the files already exists locally
        files = request.files.getlist('photoUpload[]')
        additional_data = json.loads(request.form['photoUpload-data']) if request.form['photoUpload-data'] else {}

        # evaluate input
        try:
            PImageUploadedMetadata(**additional_data)
        except ValidationError as err:
            throw_exception(str(err))

        plants = [{'key': p, 'text': p} for p in additional_data['plants']] if 'plants' in additional_data else []
        keywords = [{'keyword': k, 'text': k} for k in additional_data['keywords']] \
            if 'keywords' in additional_data else []

        # remove duplicates (already saved)
        duplicate_filenames = []
        for i, photo_upload in enumerate(files[:]):  # need to loop on copy if we want to delete within loop
            path = os.path.join(PATH_ORIGINAL_PHOTOS_UPLOADED, photo_upload.filename)
            logger.debug(f'Checking uploaded photo ({photo_upload.mimetype}) to be saved as {path}.')
            if os.path.isfile(path) or os.path.isfile(with_suffix(path, RESIZE_SUFFIX)):  # todo: better check in all
                # folders!
                files.pop(i - len(duplicate_filenames))
                duplicate_filenames.append(photo_upload.filename)
                logger.warning(f'Skipping file upload (duplicate) for: {photo_upload.filename}')

        if files:
            for photo_upload in files:
                path = os.path.join(PATH_ORIGINAL_PHOTOS_UPLOADED, photo_upload.filename)
                logger.info(f'Saving {path}.')
                photo_upload.save(path)  # we can't use object first and then save as this alters file object

                if not config.resizing_size:
                    pass

                elif not resizing_required(path, config.resizing_size):
                    logger.info(f'No resizing required.')

                else:
                    logger.info(f'Saving and resizing {path}.')
                    # add suffix to filename and resize image
                    resize_image(path=path,
                                 save_to_path=with_suffix(path, RESIZE_SUFFIX),
                                 size=config.resizing_size,
                                 quality=config.quality)
                    path = with_suffix(path, RESIZE_SUFFIX)

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

            # with lock_photo_directory:
            #     if not image_services.photo_directory:
            #         image_services.photo_directory = PhotoDirectory(PATH_ORIGINAL_PHOTOS)
            #     image_services.photo_directory.refresh_directory(plants_tagger.config_local.PATH_BASE)

            # trigger re-reading exif tags (only required if already instantiated, otherwise data is re-read anyway)
            with lock_photo_directory:
                photo_directory = get_photo_directory(instantiate=False)
                if photo_directory:
                    photo_directory.refresh_directory(PATH_BASE)
                else:
                    logger.debug('No instantiated photo directory found.')

        if files and not duplicate_filenames:
            msg = get_message(f'Successfully saved {len(files)} images.')
        else:
            msg = get_message(f'Duplicates found when saving.',
                              message_type=MessageType.WARNING,
                              additional_text='click for details',
                              description=f'Saved {[p.filename for p in files]}.'
                                          f'\nSkipped {duplicate_filenames}.')
        logger.info(msg['message'])
        results = {'action':   'Uploaded',
                   'resource': 'ImageResource',
                   'message':  msg
                   }

        # evaluate output
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def delete():
        """move the file that should be deleted to another folder (not actually deleted, currently)"""
        photo = request.get_json()

        # evaluate input
        try:
            PImage(**photo)
        except ValidationError as err:
            throw_exception(str(err))

        old_path = photo['path_full_local']
        if not os.path.isfile(old_path):
            logger.error(err_msg := f"File selected to be deleted not found: {old_path}")
            throw_exception(err_msg)

        filename = os.path.basename(old_path)
        new_path = os.path.join(PATH_DELETED_PHOTOS, filename)

        try:
            os.replace(src=old_path,
                       dst=new_path)  # silently overwrites if privileges are sufficient
        except OSError as e:
            logger.error(err_msg := f'OSError when moving file {old_path} to {new_path}', exc_info=e)
            throw_exception(err_msg, description=f'Filename: {os.path.basename(old_path)}')
        logger.info(f'Moved file {old_path} to {new_path}')

        # remove from PhotoDirectory cache
        with lock_photo_directory:
            photo_directory = get_photo_directory(instantiate=False)
            if photo_directory:
                photo_directory.remove_image_from_directory(photo)

        results = {'action':   'Deleted',
                   'resource': 'ImageResource',
                   'message':  get_message(f'Successfully deleted image',
                                           description=f'Filename: {os.path.basename(old_path)}'),
                   'photo':    photo}

        # evaluate output
        try:
            PResultsImageDeleted(**results)
        except ValidationError as err:
            throw_exception(str(err))

        # send the photo back to frontend; it will be removed from json model there
        return results, 200

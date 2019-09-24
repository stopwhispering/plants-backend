from flask_restful import Resource
from flask import request
import logging

from plants_tagger.models import get_sql_session
from plants_tagger.models.files import get_exif_tags_for_folder, write_new_exif_tags
from plants_tagger.models.orm_tables import Plant
from plants_tagger.util.json_helper import make_list_items_json_serializable, get_message

logger = logging.getLogger(__name__)


class ImageResource2(Resource):
    @staticmethod
    def get():
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

        make_list_items_json_serializable(files_data)

        logger.info(f'Returned {len(files_data)} images.')
        return {'ImagesCollection': files_data,
                'message': get_message('Loaded images from backend.',
                                       description=f'Count: {len(files_data)}')
                }, 200

    @staticmethod
    def post(**kwargs):
        if not kwargs:
            kwargs = request.get_json(force=True)
        logger.info(f"Saving updates for {len(kwargs['ImagesCollection'])} images.")
        write_new_exif_tags(kwargs['ImagesCollection'])
        return {'action':   'Saved',
                'resource': 'ImageResource',
                'message': get_message(f"Saved updates for {len(kwargs['ImagesCollection'])} images.")
                }, 200

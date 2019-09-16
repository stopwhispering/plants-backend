from flask_restful import Resource
from flask import request
import logging

from plants_tagger.models import get_sql_session
from plants_tagger.models.files import get_exif_tags_for_folder, write_new_exif_tags
from plants_tagger.models.orm_tables import Plant
from plants_tagger.util.json_helper import make_list_items_json_serializable
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)


class ImageResource2(Resource):
    @staticmethod
    def get():
        files_data, _ = get_exif_tags_for_folder()
        i = len(files_data)

        # filter out archived images (todo: required?)
        files_data = [f for f in files_data if 'keywords' not in f or 'Archiv' not in f['keywords']]
        logger.debug(f'Filter out {i - len(files_data)} images due to Archiv keyword.')

        # get plants whose images are configured to be hidden (hide-flag is set in plants table)
        plants_to_hide = get_sql_session().query(Plant).filter_by(hide=True).all()
        plants_to_hide_names = [p.plant_name for p in plants_to_hide]
        logger.debug(f'Hiding images that have only hidden plants tagged: {plants_to_hide_names}')
        # hiding = [f for f in files_data if (len(f['plants']) == 1 and f['plants'][0] in plants_to_hide_names)]
        # logger.debug(f'Hiding images: {hiding}')
        temp = [f for f in files_data if (len(f['plants']) == 1 and f['plants'][0] in plants_to_hide_names)]
        logger.error(temp)
        files_data = [f for f in files_data if not (len(f['plants']) == 1 and f['plants'][0] in plants_to_hide_names)]
        logger.debug(f'Filter out {i - len(files_data)} images due to Hide flag of the only tagged plant.')

        for image in files_data:
            if image['plants']:
                image['plants'] = [{'key': p, 'text': p} for p in image['plants']]
            if image['keywords']:
                image['keywords'] = [{'keyword': p} for p in image['keywords']]
                # image['keywords'] = [{'key': p, 'text': p} for p in image['keywords']]

        make_list_items_json_serializable(files_data)

        logger.info(f'Returned {len(files_data)} images.')

        return {'ImagesCollection': files_data,
                'message': {
                    'type': 'Information',
                    'message': 'Loaded images from backend.',
                    'additionalText': None,
                    'description': f'Count: {len(files_data)}\nResource: {parse_resource_from_request(request)}'
                    }}, 200

    @staticmethod
    def post(**kwargs):
        if not kwargs:
            kwargs = request.get_json(force=True)
        logger.info(f"Saving updates for {len(kwargs['ImagesCollection'])} images.")
        write_new_exif_tags(kwargs['ImagesCollection'])
        # try:
        #     create_entry(category=category, date_=date_, text=text)
        # except (EntryExists, CategoryNotValid) as e:
        #     return e.__repr__(), HTTP_CLIENT_ERROR
        return {'action':   'Saved',
                'resource': 'ImageResource'}, 200

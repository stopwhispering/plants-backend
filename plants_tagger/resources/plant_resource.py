from flask_restful import Resource
from flask import request
import json
import logging
import datetime

from plants_tagger.models import get_sql_session
import plants_tagger.models.files
from plants_tagger.models.files import generate_previewimage_get_rel_path, lock_photo_directory, PhotoDirectory
from plants_tagger.models.orm_tables import Plant, object_as_dict
from plants_tagger.models.update_plants import update_plants_from_list_of_dicts
from plants_tagger.util.json_helper import make_list_items_json_serializable, get_message, throw_exception
from plants_tagger import config

logger = logging.getLogger(__name__)


class PlantResource(Resource):
    @staticmethod
    def get():
        # select plants from databaes
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = get_sql_session().query(Plant)
        if config.filter_hidden:
            # noinspection PyComparisonWithNone
            query = query.filter((Plant.hide == False) | (Plant.hide == None))

        plants_obj = query.all()
        plants_list = []
        for p in plants_obj:
            plant = p.__dict__.copy()
            if '_sa_instance_state' in plant:
                del plant['_sa_instance_state']
            else:
                logger.debug('Filter hidden-flagged plants disabled.')

            # add botanical name to plants resource to facilitate usage in master view and elsewhere
            if p.taxon:
                plant['botanical_name'] = p.taxon.name

            # add path to preview image
            if plant['filename_previewimage']:  # supply relative path of original image
                rel_path_gen = generate_previewimage_get_rel_path(plant['filename_previewimage'])
                # there is a huge problem with the slashes
                plant['url_preview'] = json.dumps(rel_path_gen)[1:-1]
            else:
                plant['url_preview'] = None

            # add tags
            if p.tags:
                plant['tags'] = [object_as_dict(t) for t in p.tags]

            plants_list.append(plant)

        # get latest photo record date per plant
        null_date = datetime.date(1900, 1, 1)
        with lock_photo_directory:
            if not plants_tagger.models.files.photo_directory:
                plants_tagger.models.files.photo_directory = PhotoDirectory()
                plants_tagger.models.files.photo_directory.refresh_directory()
            plant_image_dates = plants_tagger.models.files.photo_directory.get_latest_date_per_plant()
        for plant in plants_list:
            plant['latest_image_record_date'] = plant_image_dates.get(plant['plant_name'])
            # if no image at all, use a very early date as null would sort them after late days in ui5 sorters
            # (in ui5 formatter, we will format the null_date as an empty string)
            plant['latest_image_record_date'] = plant_image_dates.get(plant['plant_name'], null_date)

        make_list_items_json_serializable(plants_list)

        return {'PlantsCollection': plants_list,
                'message': get_message(f"Loaded {len(plants_list)} plants from database.")}, 200

    @staticmethod
    def post(**kwargs):
        if not kwargs:
            kwargs = request.get_json(force=True)

        # update plants
        update_plants_from_list_of_dicts(kwargs['PlantsCollection'])

        message = f"Saved updates for {len(kwargs['PlantsCollection'])} plants."
        logger.info(message)
        return {'action': 'Saved',
                'resource': 'PlantResource',
                'message': get_message(message)
                }, 200

    @staticmethod
    def delete():
        # tag deleted plant as 'hide' in database
        plant_name = request.get_json()['plant']
        record_update: Plant = get_sql_session().query(Plant).filter_by(plant_name=plant_name).first()
        if not record_update:
            logger.error(f'Plant to be deleted not found in database: {plant_name}.')
            throw_exception(f'Plant to be deleted not found in database: {plant_name}.')
        record_update.hide = True
        get_sql_session().commit()

        message = f'Deleted plant {plant_name}'
        logger.info(message)
        return {'message':  get_message(message,
                                        description=f'Plant name: {plant_name}\nHide: True')
                }, 200

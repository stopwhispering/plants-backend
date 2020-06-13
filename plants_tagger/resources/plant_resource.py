from flask_restful import Resource
from flask import request
import logging
import datetime

from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.services.files import rename_plant_in_exif_tags
from plants_tagger.services.history import create_history_entry
from plants_tagger.models.plant_models import Plant
from plants_tagger.services.update_plants import update_plants_from_list_of_dicts
from flask_2_ui5_py import make_list_items_json_serializable, get_message, throw_exception, \
    make_dict_values_json_serializable
from plants_tagger import config

logger = logging.getLogger(__name__)
NULL_DATE = datetime.date(1900, 1, 1)


class PlantResource(Resource):
    @staticmethod
    def _get_single(plant_name):
        plant_obj = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name).first()
        if not plant_obj:
            logger.error(f'Plant not found: {plant_name}.')
            throw_exception(f'Plant not found: {plant_name}.')
        plant = plant_obj.as_dict()

        make_dict_values_json_serializable(plant)
        return {'Plant':   plant,
                'message': get_message(f"Loaded plant {plant_name} from database.")}, 200

    @staticmethod
    def _get_all():
        # select plants from databaes
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = get_sql_session().query(Plant)
        if config.filter_hidden:
            # noinspection PyComparisonWithNone
            query = query.filter((Plant.hide == False) | (Plant.hide == None))

        plants_obj = query.all()
        plants_list = []
        for p in plants_obj:
            plant = p.as_dict()
            plants_list.append(plant)

        make_list_items_json_serializable(plants_list)

        return {'PlantsCollection': plants_list,
                'message':          get_message(f"Loaded {len(plants_list)} plants from database.")}, 200

    def get(self, plant_name: str = None):
        """read plant(s) information from db"""
        if plant_name:
            return self._get_single(plant_name)
        else:
            return self._get_all()

    @staticmethod
    def post(**kwargs):
        """update existing plant"""
        if not kwargs:
            kwargs = request.get_json(force=True)

        # update plants
        update_plants_from_list_of_dicts(kwargs['PlantsCollection'])

        message = f"Saved updates for {len(kwargs['PlantsCollection'])} plants."
        logger.info(message)
        return {'action':   'Saved',
                'resource': 'PlantResource',
                'message':  get_message(message)
                }, 200

    @staticmethod
    def delete():
        """tag deleted plant as 'hide' in database"""
        plant_name = request.get_json()['plant']
        record_update: Plant = get_sql_session().query(Plant).filter_by(plant_name=plant_name).first()
        if not record_update:
            logger.error(f'Plant to be deleted not found in database: {plant_name}.')
            throw_exception(f'Plant to be deleted not found in database: {plant_name}.')
        record_update.hide = True
        get_sql_session().commit()

        message = f'Deleted plant {plant_name}'
        logger.info(message)
        return {'message': get_message(message,
                                       description=f'Plant name: {plant_name}\nHide: True')
                }, 200

    @staticmethod
    def put():
        """we use the put method to rename a plant"""
        plant_name_old = request.get_json().get('OldPlantName')
        plant_name_new = request.get_json().get('NewPlantName')

        # some validations first
        if not plant_name_old or not plant_name_new:
            throw_exception(f'Bad plant names: {plant_name_old} / {plant_name_new}')

        plant_obj = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name_old).first()
        if not plant_obj:
            throw_exception(f"Can't find plant {plant_name_old}")

        if get_sql_session().query(Plant).filter(Plant.plant_name == plant_name_new).first():
            throw_exception(f"Plant already exists: {plant_name_new}")

        # rename plant name
        plant_obj.plant_name = plant_name_new
        plant_obj.last_update = datetime.datetime.now()

        # most difficult task: exif tags use plant name not id; we need to change each plant name occurence
        # in images' exif tags
        count_modified_images = rename_plant_in_exif_tags(plant_name_old, plant_name_new)

        # only after image modifications have gone well, we can commit changes to database
        get_sql_session().commit()

        create_history_entry(description=f"Renamed to {plant_name_new}",
                             plant_id=plant_obj.id,
                             plant_name=plant_name_old,
                             commit=False)

        logger.info(f'Modified {count_modified_images} images.')
        return {'message': get_message(f'Renamed {plant_name_old} to {plant_name_new}',
                                       description=f'Modified {count_modified_images} images.')
                }, 200

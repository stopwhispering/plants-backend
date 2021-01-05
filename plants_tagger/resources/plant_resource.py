from flask_restful import Resource
from flask import request
import logging
import datetime

from pydantic.error_wrappers import ValidationError

from plants_tagger.config_local import DEMO_MODE_RESTRICT_TO_N_PLANTS
from plants_tagger.extensions.orm import get_sql_session
from plants_tagger.validation.message_validation import PConfirmation
from plants_tagger.validation.plant_validation import PResultsPlants, PPlant, PPlantsUpdateRequest, \
    PResultsPlantsUpdate, PPlantsDeleteRequest, PPlantsRenameRequest
from plants_tagger.services.image_services import rename_plant_in_image_files
from plants_tagger.services.history_services import create_history_entry
from plants_tagger.models.plant_models import Plant
from plants_tagger.services.plants_services import update_plants_from_list_of_dicts
from flask_2_ui5_py import make_list_items_json_serializable, get_message, throw_exception, \
    make_dict_values_json_serializable
from plants_tagger import config

logger = logging.getLogger(__name__)
NULL_DATE = datetime.date(1900, 1, 1)


class PlantResource(Resource):
    @staticmethod
    def _get_single(plant_name):
        """currently unused"""
        plant_obj = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name).first()
        if not plant_obj:
            logger.error(f'Plant not found: {plant_name}.')
            throw_exception(f'Plant not found: {plant_name}.')
        plant = plant_obj.as_dict()

        make_dict_values_json_serializable(plant)
        results = {'action':   'Get plant',
                   'resource': 'PlantResource',
                   'message':  get_message(f"Loaded plant {plant_name} from database."),
                   'Plant':    plant}

        # evaluate output
        try:
            PPlant(**plant)
        except ValidationError as err:
            throw_exception(str(err))
        return results, 200

    @staticmethod
    def _get_all():
        # select plants from database
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = get_sql_session().query(Plant)
        if config.filter_hidden:
            # noinspection PyComparisonWithNone
            query = query.filter((Plant.hide == False) | (Plant.hide == None))

        if DEMO_MODE_RESTRICT_TO_N_PLANTS:
            query = query.limit(DEMO_MODE_RESTRICT_TO_N_PLANTS)

        plants_obj = query.all()
        plants_list = [p.as_dict() for p in plants_obj]

        make_list_items_json_serializable(plants_list)
        results = {'action':           'Get plants',
                   'resource':         'PlantResource',
                   'message':          get_message(f"Loaded {len(plants_list)} plants from database."),
                   'PlantsCollection': plants_list}

        # evaluate output
        try:
            PResultsPlants(**results)
        except ValidationError as err:
            throw_exception(str(err))
        return results, 200

    def get(self, plant_name: str = None):
        """read plant(s) information from db"""
        if plant_name:
            return self._get_single(plant_name)
        else:
            return self._get_all()

    @staticmethod
    def post(**kwargs):
        """update existing plants"""
        if not kwargs:
            kwargs = request.get_json(force=True)

        # evaluate arguments
        try:
            PPlantsUpdateRequest(**kwargs)
        except ValidationError as err:
            throw_exception(str(err))

        # update plants
        plants_saved = update_plants_from_list_of_dicts(kwargs['PlantsCollection'])

        # serialize updated/created plants to refresh data in frontend
        plants_list = [p.as_dict() for p in plants_saved]
        make_list_items_json_serializable(plants_list)

        logger.info(message := f"Saved updates for {len(kwargs['PlantsCollection'])} plants.")
        results = {'action':   'Saved Plants',
                   'resource': 'PlantResource',
                   'message':  get_message(message),
                   'plants':   plants_list}  # return the updated/created plants

        # evaluate output
        try:
            PResultsPlantsUpdate(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def delete():
        """tag deleted plant as 'hide' in database"""

        # parse & evaluate arguments
        args = None
        try:
            args = PPlantsDeleteRequest(**request.get_json())
        except ValidationError as err:
            throw_exception(str(err))

        record_update: Plant = get_sql_session().query(Plant).filter_by(plant_name=args.plant).first()
        if not record_update:
            logger.error(f'Plant to be deleted not found in database: {args.plant}.')
            throw_exception(f'Plant to be deleted not found in database: {args.plant}.')
        record_update.hide = True
        get_sql_session().commit()

        logger.info(message := f'Deleted plant {args.plant}')
        results = {'action':   'Deleted plant',
                   'resource': 'PlantResource',
                   'message':  get_message(message,
                                           description=f'Plant name: {args.plant}\nHide: True')
                   }

        # evaluate output  # todo
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

    @staticmethod
    def put():
        """we use the put method to rename a plant"""
        # parse & evaluate arguments
        args = None
        try:
            args = PPlantsRenameRequest(**request.get_json())
        except ValidationError as err:
            throw_exception(str(err))

        plant_obj = get_sql_session().query(Plant).filter(Plant.plant_name == args.OldPlantName).first()
        if not plant_obj:
            throw_exception(f"Can't find plant {args.OldPlantName}")

        if get_sql_session().query(Plant).filter(Plant.plant_name == args.NewPlantName).first():
            throw_exception(f"Plant already exists: {args.NewPlantName}")

        # rename plant name
        plant_obj.plant_name = args.NewPlantName
        plant_obj.last_update = datetime.datetime.now()

        # most difficult task: exif tags use plant name not id; we need to change each plant name occurence
        # in images' exif tags
        count_modified_images = rename_plant_in_image_files(args.OldPlantName, args.NewPlantName)

        # only after image modifications have gone well, we can commit changes to database
        get_sql_session().commit()

        create_history_entry(description=f"Renamed to {args.NewPlantName}",
                             plant_id=plant_obj.id,
                             plant_name=args.OldPlantName,
                             commit=False)

        logger.info(f'Modified {count_modified_images} images.')
        results = {'action':   'Renamed plant',
                   'resource': 'PlantResource',
                   'message':  get_message(f'Renamed {args.OldPlantName} to {args.NewPlantName}',
                                           description=f'Modified {count_modified_images} images.')}
        # evaluate output  # todo
        try:
            PConfirmation(**results)
        except ValidationError as err:
            throw_exception(str(err))

        return results, 200

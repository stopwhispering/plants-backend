from flask_restful import Resource
from flask import request
import json
import logging
import datetime

from plants_tagger.models import get_sql_session
import plants_tagger.models.files
from plants_tagger.models.files import generate_previewimage_get_rel_path, lock_photo_directory, PhotoDirectory
from plants_tagger.models.orm_tables import Plant, Botany, Measurement
from plants_tagger.models.os_paths import PATH_ORIGINAL_PHOTOS
from plants_tagger.models.update_measurements import update_measurements_from_list_of_dicts
from plants_tagger.models.update_plants import update_plants_from_list_of_dicts
from plants_tagger.util.json_helper import make_list_items_json_serializable
from plants_tagger import config
from plants_tagger.util.util import parse_resource_from_request

logger = logging.getLogger(__name__)


class PlantResource(Resource):
    @staticmethod
    def get():
        plants_obj = get_sql_session().query(Plant).all()

        # unfortunately, __dict__ does not (always) include taxon (todo: try again later)
        # plants_list = [p.__dict__ for p in plants_obj]
        # _ = [p.pop('_sa_instance_state') for p in plants_list]  # remove instance state objects
        plants_list = []
        for p in plants_obj:
            plant = p.__dict__.copy()
            if '_sa_instance_state' in plant:
                del plant['_sa_instance_state']
            # plant.pop('_sa_instance_state')
            if p.taxon:
                plant['botanical_name'] = p.taxon.name
                plant['taxon'] = p.taxon.__dict__.copy()
                if '_sa_instance_state' in plant['taxon']:
                    del plant['taxon']['_sa_instance_state']
                a = 1

            plants_list.append(plant)

        # add information from botany table
        # todo remove this old botany
        for p in plants_list:
            if p['species']:
                bot = get_sql_session().query(Botany).filter(Botany.species == p['species']).first()
                if bot:
                    p['botany'] = bot.__dict__.copy()
                    if '_sa_instance_state' in p['botany']:
                        del p['botany']['_sa_instance_state']

        # add path to preview image
            if p['filename_previewimage']:  # supply relative path of original image
                # logger.debug(f"Preview Image for {p['plant_name']}: {p['filename_previewimage']}")
                rel_path_gen = generate_previewimage_get_rel_path(p['filename_previewimage'])
                # there is a huge problem with the slashes
                p['url_preview'] = json.dumps(rel_path_gen)[1:-1]
            else:
                p['url_preview'] = None

        # add measurements
            measurements = get_sql_session().query(Measurement).filter(Measurement.plant_name == p[
                 'plant_name']).all()
            if measurements:
                measurements = [m.__dict__.copy() for m in measurements]
                for m in measurements:
                    del m['_sa_instance_state']
                p['measurements'] = measurements

        # remove hidden
        if config.filter_hidden:
            count = len(plants_list)
            plants_list = [p for p in plants_list if not p['hide']]
            logger.debug(f'Filter out {count-len(plants_list)} plants due to Hide flag.')
        else:
            logger.debug('Filter hidden-flagged plants disabled.')

        # get latest photo record date per plant
        # todo: maybe cache in database; reading this here renders loading plants and images in parallel impossible
        # todo: move above in for loop? but at current position, images may be loaded already
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

        # # todo: all
        # for plant in plants_list:
        #     plant['origin'] = [
        #         {'key': 'generation_origin', 'text': plant['generation_origin'], 'title': 'Origin',
        #             'value_state': 'Information', 'visible': True},
        #         {'key': 'generation_notes', 'text': plant['generation_notes'], 'title': 'Notes', 'value_state':
        #             'Information', 'visible': True if plant['generation_notes'] else False},
        #         {'key': 'generation_type', 'text': plant['generation_type'], 'title': 'Type', 'value_state':
        #             'Information', 'visible': True if plant['generation_type'] else False},
        #         {'key': 'generation_date', 'text': plant['generation_date'], 'title': 'Date ', 'value_state':
        #             'Information', 'visible': True if plant['generation_date'] else False},
        #         {'key': 'mother_plant', 'text': plant['mother_plant'], 'title': 'Mother plant', 'value_state':
        #             'Information', 'visible': True if plant['mother_plant'] else False}
        #         ]
        #
        #     plant['misc'] = [
        #         {'key': 'species', 'text': plant['species'], 'title': 'Species', 'value_state': 'Success' if
        #                                                                                         plant.get('botany') else 'Error'},
        #         # last_update is read-only, i.e. not saved from gui input
        #         {'key': 'count', 'text': plant['count'], 'title': 'Count', 'value_state':
        #             'Information'}
        #         ]

        make_list_items_json_serializable(plants_list)

        return {'PlantsCollection': plants_list,
                'meta': 'dummy'}, 200

    @staticmethod
    def post(**kwargs):
        if not kwargs:
            kwargs = request.get_json(force=True)

        # update plants
        update_plants_from_list_of_dicts(kwargs['PlantsCollection'])

        # update measurements & events if existing
        measurements = [p['measurements'] for p in kwargs['PlantsCollection'] if 'measurements' in p]
        # unflatten
        measurements = [m for sublist in measurements for m in sublist]
        if measurements:
            update_measurements_from_list_of_dicts(measurements)

        return {'action': 'Saved',
                'resource': 'PlantResource'}, 200

    @staticmethod
    def delete():
        # tag deleted plant as 'hide' in database
        plant_name = request.get_json()['plant']
        record_update: Plant = get_sql_session().query(Plant).filter_by(plant_name=plant_name).first()
        if not record_update:
            raise ValueError(f'Plant to be deleted not found in database: {plant_name}.')
        record_update.hide = True
        get_sql_session().commit()

        return {'message':  {
            'type':           'Information',
            'message':        f'Deleted plant {plant_name}',
            'additionalText': None,
            'description':    f'Plant name: {plant_name}'
                              f'\nResource: {parse_resource_from_request(request)}'
                              f'\nHide: True'
            }
                }, 200

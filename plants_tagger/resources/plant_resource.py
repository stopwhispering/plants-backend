from flask_restful import Resource
from flask import request
import json
import logging
import datetime

from sqlalchemy.orm import make_transient
from sqlalchemy_utils import get_referencing_foreign_keys, dependent_objects

from package_flask_2_ui5_py.flask_2_ui5_py import make_dict_values_json_serializable
from plants_tagger.models import get_sql_session
import plants_tagger.models.files
from plants_tagger.models.files import generate_previewimage_get_rel_path, lock_photo_directory, PhotoDirectory, \
    rename_plant_in_exif_tags
from plants_tagger.models.orm_tables import Plant, object_as_dict, Trait, TraitCategory
from plants_tagger.models.update_plants import update_plants_from_list_of_dicts
from flask_2_ui5_py import make_list_items_json_serializable, get_message, throw_exception
from plants_tagger import config

logger = logging.getLogger(__name__)
NULL_DATE = datetime.date(1900, 1, 1)


class PlantResource(Resource):
    def _get_single(self, plant_name):
        plant_obj = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name).first()
        if not plant_obj:
            logger.error(f'Plant not found: {plant_name}.')
            throw_exception(f'Plant not found: {plant_name}.')
        plant = self._assemble_plant(plant_obj)

        make_dict_values_json_serializable(plant)
        return {'Plant': plant,
                'message': get_message(f"Loaded plant {plant_name} from database.")}, 200

    @staticmethod
    def _assemble_plant(plant_obj: Plant) -> dict:
        plant = plant_obj.__dict__.copy()
        if '_sa_instance_state' in plant:
            del plant['_sa_instance_state']
        else:
            logger.debug('Filter hidden-flagged plants disabled.')

        # add botanical name to plants resource to facilitate usage in master view and elsewhere
        # include authors as well
        if plant_obj.taxon:
            plant['botanical_name'] = plant_obj.taxon.name
            plant['taxon_authors'] = plant_obj.taxon.authors

        # add path to preview image
        if plant['filename_previewimage']:  # supply relative path of original image
            rel_path_gen = generate_previewimage_get_rel_path(plant['filename_previewimage'])
            # there is a huge problem with the slashes
            plant['url_preview'] = json.dumps(rel_path_gen)[1:-1]
        else:
            plant['url_preview'] = None

        # add tags
        if plant_obj.tags:
            plant['tags'] = [object_as_dict(t) for t in plant_obj.tags]

        # add current soil
        soil_events = [e for e in plant_obj.events if e.soil]
        if soil_events:
            soil_events.sort(key=lambda e: e.date, reverse=True)
            plant['current_soil'] = {'soil_name': soil_events[0].soil.soil_name,
                                     'date':      soil_events[0].date}
        else:
            plant['current_soil'] = None

        # get latest photo record date per plant
        with lock_photo_directory:
            if not plants_tagger.models.files.photo_directory:
                plants_tagger.models.files.photo_directory = PhotoDirectory()
                plants_tagger.models.files.photo_directory.refresh_directory()
            plant['latest_image_record_date'] = plants_tagger.models.files.photo_directory\
                .get_latest_date_per_plant(plant['plant_name'])

        return plant

    def _get_all(self):
        # select plants from databaes
        # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
        query = get_sql_session().query(Plant)
        if config.filter_hidden:
            # noinspection PyComparisonWithNone
            query = query.filter((Plant.hide == False) | (Plant.hide == None))

        plants_obj = query.all()
        plants_list = []
        for p in plants_obj:
            plant = self._assemble_plant(p)
            plants_list.append(plant)

        make_list_items_json_serializable(plants_list)

        return {'PlantsCollection': plants_list,
                'message': get_message(f"Loaded {len(plants_list)} plants from database.")}, 200

    def get(self, plant_name: str = None):
        if plant_name:
            return self._get_single(plant_name)
        else:
            return self._get_all()

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

    @staticmethod
    def put():
        # we use the put method to rename a plant
        # as (a) plant_name is primary key in the database table and (b) images are tagged with their current
        # plant names in their exif tags, this is a quite complicated task
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

        # get all usages of plant in other tables (we need to do that before expunging)
        dependencies = list(dependent_objects(plant_obj, get_referencing_foreign_keys(plant_obj)))

        # get old plant object out of session so we can work on the key column
        get_sql_session().expunge(plant_obj)  # expunge the object from session
        make_transient(plant_obj)  # http://docs.sqlalchemy.org/en/rel_1_1/orm/session_api.html#sqlalchemy.orm.session.make_transient

        # rename plant name so we get a new table entry
        plant_obj.plant_name = plant_name_new
        plant_obj.last_update = datetime.datetime.now()
        get_sql_session().add(plant_obj)

        # redirect all usages of old plant to the new plant (e.g. in tags table)
        for dep in dependencies:
            plant_fk = getattr(dep, 'plant')
            if not plant_fk:
                throw_exception(f"Technical error. Found dependency without plant attribute. Canceled renaming.")
            setattr(dep, 'plant', plant_obj)

        # next, we need to change all image files where plant was tagged with the old plant name
        # (images are not tagged in database but in the files' exif file extensions)
        count_modified_images = rename_plant_in_exif_tags(plant_name_old, plant_name_new)

        # after image modifications have gone well, we can commit changes to database
        get_sql_session().commit()

        # finally, set the old plant to hide (same thing as when deleting from the frontend)
        plant_obj_obsolete = get_sql_session().query(Plant).filter(Plant.plant_name == plant_name_old).first()
        plant_obj_obsolete.hide = True
        get_sql_session().commit()

        logger.info(f'Modified {count_modified_images} images.')
        return {'message':  get_message(f'Renamed {plant_name_old} to {plant_name_new}',
                                        description=f'Modified {count_modified_images} images.')
                }, 200

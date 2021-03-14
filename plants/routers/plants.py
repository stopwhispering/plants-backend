from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging
import datetime
from pydantic.error_wrappers import ValidationError
from starlette.requests import Request

from plants.util.ui_utils import (make_list_items_json_serializable, get_message, throw_exception,
                                  make_dict_values_json_serializable)
from plants.dependencies import get_db
from plants.config_local import DEMO_MODE_RESTRICT_TO_N_PLANTS
from plants.validation.plant_validation import PResultsPlants, PPlant
from plants.models.plant_models import Plant
from plants import config
from plants.services.history_services import create_history_entry
from plants.services.image_services import rename_plant_in_image_files
from plants.services.plants_services import update_plants_from_list_of_dicts
from plants.validation.message_validation import PConfirmation
from plants.validation.plant_validation import PPlantsUpdateRequest, PResultsPlantsUpdate, PPlantsDeleteRequest, \
    PPlantsRenameRequest

logger = logging.getLogger(__name__)

NULL_DATE = datetime.date(1900, 1, 1)

router = APIRouter(
        prefix="/plants",
        tags=["plants"],
        responses={404: {"description": "Not found"}},
        )


def _get_single(plant_name: str, db: Session, request: Request):
    """currently unused"""
    plant_obj = db.query(Plant).filter(Plant.plant_name == plant_name).first()
    if not plant_obj:
        logger.error(f'Plant not found: {plant_name}.')
        throw_exception(f'Plant not found: {plant_name}.', request=request)
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
        throw_exception(str(err), request=request)
    return results


def _get_all(db: Session, request: Request):
    # select plants from database
    # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
    query = db.query(Plant)
    if config.filter_hidden:
        # noinspection PyComparisonWithNone
        # sqlite does not like "is None" and pylint doesn't like "== None"
        query = query.filter((Plant.hide.is_(False)) | (Plant.hide.is_(None)))

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
        throw_exception(str(err), request=request)
    return results


@router.get("/")
async def get_plants(request: Request, plant_name: str = None, db: Session = Depends(get_db)):
    """read plant(s) information from db"""
    if plant_name:
        return _get_single(plant_name, db, request)
    else:
        return _get_all(db, request)


@router.post("/")
def modify_plants(request: Request, data: PPlantsUpdateRequest, db: Session = Depends(get_db)):
    """update existing or create new plants"""
    plants_modified = data.PlantsCollection

    # update plants
    plants_saved = update_plants_from_list_of_dicts(plants_modified, db)

    # serialize updated/created plants to refresh data in frontend
    plants_list = [p.as_dict() for p in plants_saved]
    make_list_items_json_serializable(plants_list)

    logger.info(message := f"Saved updates for {len(plants_modified)} plants.")
    results = {'action':   'Saved Plants',
               'resource': 'PlantResource',
               'message':  get_message(message),
               'plants':   plants_list}  # return the updated/created plants

    # evaluate output
    try:
        PResultsPlantsUpdate(**results)
    except ValidationError as err:
        throw_exception(str(err), request=request)

    return results


@router.delete("/")
def delete_plant(request: Request, data: PPlantsDeleteRequest, db: Session = Depends(get_db)):
    """tag deleted plant as 'hide' in database"""

    args = data

    record_update: Plant = db.query(Plant).filter_by(plant_name=args.plant).first()
    if not record_update:
        logger.error(f'Plant to be deleted not found in database: {args.plant}.')
        throw_exception(f'Plant to be deleted not found in database: {args.plant}.', request=request)
    record_update.hide = True
    db.commit()

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
        throw_exception(str(err), request=request)

    return results


@router.put("/")
def rename_plant(request: Request, data: PPlantsRenameRequest, db: Session = Depends(get_db)):
    """we use the put method to rename a plant"""
    args = data

    plant_obj = db.query(Plant).filter(Plant.plant_name == args.OldPlantName).first()
    if not plant_obj:
        throw_exception(f"Can't find plant {args.OldPlantName}", request=request)

    if db.query(Plant).filter(Plant.plant_name == args.NewPlantName).first():
        throw_exception(f"Plant already exists: {args.NewPlantName}", request=request)

    # rename plant name
    plant_obj.plant_name = args.NewPlantName
    plant_obj.last_update = datetime.datetime.now()

    # most difficult task: exif tags use plant name not id; we need to change each plant name occurence
    # in images' exif tags
    count_modified_images = rename_plant_in_image_files(args.OldPlantName, args.NewPlantName)

    # only after image modifications have gone well, we can commit changes to database
    db.commit()

    create_history_entry(description=f"Renamed to {args.NewPlantName}",
                         db=db,
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
        throw_exception(str(err), request=request)

    return results

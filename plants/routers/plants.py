from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session,  subqueryload
import logging
import datetime
from starlette.requests import Request

from plants import config
from plants.models.taxon_models import Taxon
from plants.util.ui_utils import (make_list_items_json_serializable, get_message, throw_exception,
                                  make_dict_values_json_serializable)
from plants.dependencies import get_db
from plants.validation.plant_validation import PResultsPlants, PPlant
from plants.models.plant_models import Plant
from plants.services.history_services import create_history_entry
from plants.services.image_services import rename_plant_in_image_files
from plants.services.plants_services import update_plants_from_list_of_dicts, deep_clone_plant, get_plant_as_dict
from plants.validation.message_validation import PConfirmation
from plants.validation.plant_validation import (PPlantsUpdateRequest, PResultsPlantsUpdate, PPlantsDeleteRequest,
                                                PPlantsRenameRequest)

logger = logging.getLogger(__name__)

NULL_DATE = datetime.date(1900, 1, 1)

router = APIRouter(
        prefix="/plants",
        tags=["plants"],
        responses={404: {"description": "Not found"}},
        )


@router.get("/{plant_id}", response_model=PPlant)
async def get_plant(request: Request,
                    plant_id: int,
                    db: Session = Depends(get_db)
                    ):
    """
    read plant information from db
    currently unused
    """
    plant_obj = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant_obj:
        throw_exception(f'Plant not found: {plant_id}.', request=request)
    # plant = plant_obj.as_dict()
    plant = get_plant_as_dict(plant_obj)

    make_dict_values_json_serializable(plant)
    return plant


@router.get("/", response_model=PResultsPlants)
async def get_plants(db: Session = Depends(get_db)):
    """read (almost unfiltered) plants information from db"""
    # select plants from database
    # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
    query = db.query(Plant)
    if config.filter_hidden_plants:
        # sqlite does not like "is None" and pylint doesn't like "== None"
        query = query.filter((Plant.hide.is_(False)) | (Plant.hide.is_(None)))

    if config.n_plants:
        query = query.order_by(Plant.plant_name).limit(config.n_plants)

    # save around 30% of time using subqueryload instead of lazyload (default)
    plants_obj = query.options(subqueryload(Plant.parent_plant).subqueryload(Plant.descendant_plants),
                               subqueryload(Plant.parent_plant_pollen).subqueryload(Plant.descendant_plants),
                               subqueryload(Plant.taxon).subqueryload(Taxon.plants),
                               subqueryload(Plant.tags),
                               subqueryload(Plant.events),
                               subqueryload(Plant.images),
                               ).all()
    plants_list = [get_plant_as_dict(p) for p in plants_obj]

    make_list_items_json_serializable(plants_list)
    results = {'action':           'Get plants',
               'resource':         'PlantResource',
               'message':          get_message(f"Loaded {len(plants_list)} plants from database."),
               'PlantsCollection': plants_list}

    return results


@router.post("/{plant_id}/clone", response_model=PResultsPlantsUpdate)
def clone_plant(
        request: Request,
        plant_id: int,
        plant_name_clone: str,
        db: Session = Depends(get_db),
        ):
    """
    clone plant with supplied plant_id; include duplication of events, photo_file assignments, and
    properties
    """
    plant_original = Plant.get_plant_by_plant_id(plant_id, db, raise_exception=True)

    if not plant_name_clone or Plant.get_plant_by_plant_name(plant_name_clone, db):
        throw_exception(f'Cloned Plant Name may not exist, yet: {plant_name_clone}.', request=request)

    deep_clone_plant(plant_original, plant_name_clone, db)

    plant_clone = Plant.get_plant_by_plant_name(plant_name_clone, db, raise_exception=True)
    create_history_entry(description=f"Cloned from {plant_original.plant_name} ({plant_original.id})",
                         db=db,
                         plant_id=plant_clone.id,
                         plant_name=plant_clone.plant_name,
                         commit=True)

    logger.info(msg := f"Cloned {plant_original.plant_name} ({plant_original.id}) "
                       f"into {plant_clone.plant_name} ({plant_clone.id})")
    results = {'action':   'Renamed plant',
               'resource': 'PlantResource',
               'message':  get_message(msg, description=msg),
               # 'plants':   [plant_clone.as_dict()]}
               'plants':   [get_plant_as_dict(plant_clone)]}

    return results


@router.post("/", response_model=PResultsPlantsUpdate)
def modify_plants(data: PPlantsUpdateRequest, db: Session = Depends(get_db)):
    """
    update existing or create new plants
    if no id is supplied, a new plant is created having the supplied attributes (only
    plant_name is mandatory, others may be provided)
    """
    plants_modified = data.PlantsCollection

    # update plants
    plants_saved = update_plants_from_list_of_dicts(plants_modified, db)

    # serialize updated/created plants to refresh data in frontend
    # plants_list = [p.as_dict() for p in plants_saved]
    plants_list = [get_plant_as_dict(p) for p in plants_saved]
    make_list_items_json_serializable(plants_list)

    logger.info(message := f"Saved updates for {len(plants_modified)} plants.")
    results = {'action':   'Saved Plants',
               'resource': 'PlantResource',
               'message':  get_message(message),
               'plants':   plants_list}  # return the updated/created plants

    return results


@router.delete("/", response_model=PConfirmation)
def delete_plant(request: Request, data: PPlantsDeleteRequest, db: Session = Depends(get_db)):
    """tag deleted plant as 'hide' in database"""

    args = data

    record_update: Plant = db.query(Plant).filter_by(id=args.plant_id).first()
    if not record_update:
        logger.error(f'Plant to be deleted not found in database: {args.plant_id}.')
        throw_exception(f'Plant to be deleted not found in database: {args.plant_id}.', request=request)
    record_update.hide = True
    db.commit()

    logger.info(message := f'Deleted plant {record_update.plant_name}')
    results = {'action':   'Deleted plant',
               'resource': 'PlantResource',
               'message':  get_message(message,
                                       description=f'Plant name: {record_update.plant_name}\nHide: True')
               }

    return results


@router.put("/", response_model=PConfirmation)
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

    # most difficult task: jpg exif tags use plant name not id; we need to change each plant name occurence
    count_modified_images = rename_plant_in_image_files(plant=plant_obj,
                                                        plant_name_old=args.OldPlantName)

    # only after photo_file modifications have gone well, we can commit changes to database
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

    return results

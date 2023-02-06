from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging
import datetime
from starlette.requests import Request

from plants.shared.message_services import throw_exception, get_message
from plants.dependencies import get_db, valid_plant
from plants.modules.plant.models import Plant
from plants.shared.history_services import create_history_entry
from plants.modules.image.services import rename_plant_in_image_files
from plants.modules.plant.services import update_plants_from_list_of_dicts, deep_clone_plant, fetch_plants, \
    generate_subsequent_plant_name
from plants.shared.message_schemas import BConfirmation, FBMajorResource
from plants.modules.plant.schemas import (BPlantsRenameRequest, BResultsPlants, FPlantsUpdateRequest,
                                          BResultsPlantsUpdate, BResultsPlantCloned, BResultsProposeSubsequentPlantName)

logger = logging.getLogger(__name__)

NULL_DATE = datetime.date(1900, 1, 1)

router = APIRouter(
        prefix="/plants",
        tags=["plants"],
        responses={404: {"description": "Not found"}},
        )


@router.post("/{plant_id}/clone", response_model=BResultsPlantCloned)
def clone_plant(
        request: Request,
        plant_name_clone: str,
        plant_original: Plant = Depends(valid_plant),
        db: Session = Depends(get_db),
        ):
    """
    clone plant with supplied plant_id; include duplication of events, photo_file assignments, and
    properties
    """
    if not plant_name_clone or Plant.by_name(plant_name_clone, db):
        throw_exception(f'Cloned Plant Name may not exist, yet: {plant_name_clone}.', request=request)

    deep_clone_plant(plant_original, plant_name_clone, db)

    plant_clone = Plant.by_name(plant_name_clone, db, raise_if_not_exists=True)
    create_history_entry(description=f"Cloned from {plant_original.plant_name} ({plant_original.id})",
                         db=db,
                         plant_id=plant_clone.id,
                         plant_name=plant_clone.plant_name,
                         commit=False)

    logger.info(msg := f"Cloned {plant_original.plant_name} ({plant_original.id}) "
                       f"into {plant_clone.plant_name} ({plant_clone.id})")

    db.commit()
    results = {'action':   'Renamed plant',
               'message':  get_message(msg, description=msg),
               'plant':   plant_clone}

    return results


# @router.post("/", response_model=PResultsPlantsUpdate)
@router.post("/", response_model=BResultsPlantsUpdate)
def create_or_update_plants(data: FPlantsUpdateRequest, db: Session = Depends(get_db)):
    """
    update existing or create new plants
    if no id is supplied, a new plant is created having the supplied attributes (only
    plant_name is mandatory, others may be provided)
    """
    plants_modified = data.PlantsCollection

    # update plants
    plants_saved = update_plants_from_list_of_dicts(plants_modified, db)

    logger.info(message := f"Saved updates for {len(plants_modified)} plants.")
    results = {'action': 'Saved Plants',
               'resource': FBMajorResource.PLANT,
               'message': get_message(message),
               'plants': plants_saved}  # return the updated/created plants

    return results


@router.delete("/{plant_id}", response_model=BConfirmation)
def delete_plant(plant: Plant = Depends(valid_plant), db: Session = Depends(get_db)):
    """tag deleted plant as 'deleted' in database"""
    plant.deleted = True
    db.commit()

    logger.info(message := f'Deleted plant {plant.plant_name}')
    results = {'action':   'Deleted plant',
               'message':  get_message(message,
                                       description=f'Plant name: {plant.plant_name}\nDeleted: True')
               }

    return results


@router.put("/", response_model=BConfirmation)
def rename_plant(request: Request, args: BPlantsRenameRequest, db: Session = Depends(get_db)):
    """we use the put method to rename a plant"""  # todo use id
    plant = Plant.by_id(args.plant_id, db, raise_if_not_exists=True)
    assert plant.plant_name == args.old_plant_name
    # plant_obj = Plant.get_plant_by_plant_name(args.OldPlantName, db, raise_exception=True)

    if db.query(Plant).filter(Plant.plant_name == args.new_plant_name).first():
        throw_exception(f"Plant already exists: {args.new_plant_name}", request=request)

    # rename plant name
    plant.plant_name = args.new_plant_name

    # most difficult task: jpg exif tags use plant name not id; we need to change each plant name occurence
    count_modified_images = rename_plant_in_image_files(plant=plant,
                                                        plant_name_old=args.old_plant_name)

    create_history_entry(description=f"Renamed to {args.new_plant_name}",
                         db=db,
                         plant_id=plant.id,
                         plant_name=args.old_plant_name,
                         commit=False)

    # only after photo_file modifications have gone well, we can commit changes to database
    db.commit()

    logger.info(f'Modified {count_modified_images} images.')
    results = {'action':   'Renamed plant',
               'message':  get_message(f'Renamed {args.old_plant_name} to {args.new_plant_name}',
                                       description=f'Modified {count_modified_images} images.')}

    return results


@router.get("/", response_model=BResultsPlants)
async def get_plants(db: Session = Depends(get_db)):
    """read (almost unfiltered) plants information from db"""
    plants = fetch_plants(db)
    results = {'action':           'Get plants',
               'message':          get_message(f"Loaded {len(plants)} plants from database."),
               'PlantsCollection': plants}

    return results


@router.post("/propose_subsequent_plant_name/{original_plant_name}", response_model=BResultsProposeSubsequentPlantName)
async def propose_subsequent_plant_name(original_plant_name: str):
    """
    derive subsequent name for supplied plant name, e.g. "Aloe depressa VI" for "Aloe depressa V"
    """
    subsequent_plant_name = generate_subsequent_plant_name(original_plant_name)
    return {
        'original_plant_name': original_plant_name,
        'subsequent_plant_name': subsequent_plant_name
    }

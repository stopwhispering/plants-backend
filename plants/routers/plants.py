from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, subqueryload
import logging
import datetime
from starlette.requests import Request

from plants import config
from plants.util.ui_utils import (get_message, throw_exception)
from plants.dependencies import get_db
from plants.models.plant_models import Plant
from plants.services.history_services import create_history_entry
from plants.services.image_services import rename_plant_in_image_files
from plants.services.plants_services import update_plants_from_list_of_dicts, deep_clone_plant
from plants.validation.message_validation import BConfirmation, FBMajorResource
from plants.validation.plant_validation import (FPlantsDeleteRequest,
                                                BPlantsRenameRequest, BResultsPlants, FPlantsUpdateRequest,
                                                BResultsPlantsUpdate, BResultsPlantCloned)

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


@router.delete("/", response_model=BConfirmation)
def delete_plant(request: Request, data: FPlantsDeleteRequest, db: Session = Depends(get_db)):
    """tag deleted plant as 'deleted' in database"""

    args = data

    record_update: Plant = db.query(Plant).filter_by(id=args.plant_id).first()
    if not record_update:
        logger.error(f'Plant to be deleted not found in database: {args.plant_id}.')
        throw_exception(f'Plant to be deleted not found in database: {args.plant_id}.', request=request)
    record_update.deleted = True
    db.commit()

    logger.info(message := f'Deleted plant {record_update.plant_name}')
    results = {'action':   'Deleted plant',
               'message':  get_message(message,
                                       description=f'Plant name: {record_update.plant_name}\nDeleted: True')
               }

    return results


@router.put("/", response_model=BConfirmation)
def rename_plant(request: Request, data: BPlantsRenameRequest, db: Session = Depends(get_db)):
    """we use the put method to rename a plant"""  # todo use id
    args = data

    plant_obj = db.query(Plant).filter(Plant.plant_name == args.OldPlantName).first()
    if not plant_obj:
        throw_exception(f"Can't find plant {args.OldPlantName}", request=request)

    if db.query(Plant).filter(Plant.plant_name == args.NewPlantName).first():
        throw_exception(f"Plant already exists: {args.NewPlantName}", request=request)

    # rename plant name
    plant_obj.plant_name = args.NewPlantName
    # plant_obj.last_update = datetime.datetime.now()

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
               'message':  get_message(f'Renamed {args.OldPlantName} to {args.NewPlantName}',
                                       description=f'Modified {count_modified_images} images.')}

    return results


@router.get("/", response_model=BResultsPlants)
async def get_plants(db: Session = Depends(get_db)):
    """read (almost unfiltered) plants information from db"""
    # select plants from database
    # filter out hidden ("deleted" in frontend but actually only flagged hidden) plants
    query = db.query(Plant)
    if config.filter_hidden_plants:
        # sqlite does not like "is None" and pylint doesn't like "== None"
        # query = query.filter((Plant.hide.is_(False)) | (Plant.hide.is_(None)))
        query = query.filter(Plant.deleted.is_(False))

    if config.n_plants:
        query = query.order_by(Plant.plant_name).limit(config.n_plants)

    # early-load all relationship tables for Plant model relevant for PResultsPlants
    # to save around 90% (postgres) of the time in comparison to lazy loading (80% for sqlite)
    query = query.options(
        subqueryload(Plant.parent_plant),
        subqueryload(Plant.parent_plant_pollen),

        subqueryload(Plant.tags),
        subqueryload(Plant.same_taxon_plants),
        subqueryload(Plant.sibling_plants),

        subqueryload(Plant.descendant_plants),
        subqueryload(Plant.descendant_plants_pollen),
        # subqueryload(Plant.descendant_plants_all),  # property

        subqueryload(Plant.taxon),
        # subqueryload(Plant.taxon_authors),  # property

        subqueryload(Plant.events),
        # subqueryload(Plant.current_soil),  # property

        subqueryload(Plant.images),
        # subqueryload(Plant.latest_image),  # property

        # subqueryload(Plant.property_values_plant),  # not required
        # subqueryload(Plant.image_to_plant_associations),  # not required
        # subqueryload(Plant.florescences),  # not required
    )
    plants_obj = query.all()
    results = {'action':           'Get plants',
               'message':          get_message(f"Loaded {len(plants_obj)} plants from database."),
               'PlantsCollection': plants_obj}

    return results

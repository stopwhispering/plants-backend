import datetime
import logging

from fastapi import APIRouter, Depends
from starlette import status as starlette_status

from plants.dependencies import (
    get_event_dal,
    get_history_dal,
    get_image_dal,
    get_plant_dal,
    get_taxon_dal,
    valid_plant,
)
from plants.exceptions import PlantAlreadyExists
from plants.modules.event.event_dal import EventDAL
from plants.modules.image.image_dal import ImageDAL
from plants.modules.image.services import rename_plant_in_image_files
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.plant.schemas import (
    BPlantsRenameRequest,
    BResultsPlantCloned,
    BResultsPlants,
    BResultsPlantsUpdate,
    BResultsProposeSubsequentPlantName,
    FPlantsUpdateRequest,
)
from plants.modules.plant.services import (
    deep_clone_plant,
    fetch_plants,
    generate_subsequent_plant_name,
    update_plants_from_list_of_dicts,
)
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.enums import MajorResource
from plants.shared.history_dal import HistoryDAL
from plants.shared.history_services import create_history_entry
from plants.shared.message_schemas import BConfirmation
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)

NULL_DATE = datetime.date(1900, 1, 1)

router = APIRouter(
    prefix="/plants",
    tags=["plants"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/{plant_id}/clone",
    response_model=BResultsPlantCloned,
    status_code=starlette_status.HTTP_201_CREATED,
)
async def clone_plant(
    plant_name_clone: str,
    plant_original: Plant = Depends(valid_plant),
    plant_dal: PlantDAL = Depends(get_plant_dal),
    event_dal: EventDAL = Depends(get_event_dal),
    history_dal: HistoryDAL = Depends(get_history_dal),
):
    """clone plant with supplied plant_id; include duplication of events; excludes
    regular image assignments (only to events)"""
    if not plant_name_clone or await plant_dal.exists(plant_name_clone):
        raise PlantAlreadyExists(plant_name_clone)

    await deep_clone_plant(
        plant_original,
        plant_name_clone,
        plant_dal=plant_dal,
        event_dal=event_dal,
        # property_dal=property_dal,
    )

    plant_clone = await plant_dal.by_name(plant_name_clone)
    await create_history_entry(
        description=f"Cloned from {plant_original.plant_name} ({plant_original.id})",
        history_dal=history_dal,
        plant_dal=plant_dal,
        plant_id=plant_clone.id,
        plant_name=plant_clone.plant_name,
    )

    logger.info(
        msg := f"Cloned {plant_original.plant_name} ({plant_original.id}) "
        f"into {plant_clone.plant_name} ({plant_clone.id})"
    )

    results = {
        "action": "Renamed plant",
        "message": get_message(msg, description=msg),
        "plant": plant_clone,
    }

    return results


# @router.post("/", response_model=PResultsPlantsUpdate)
@router.post("/", response_model=BResultsPlantsUpdate)
async def create_or_update_plants(
    data: FPlantsUpdateRequest,
    plant_dal: PlantDAL = Depends(get_plant_dal),
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
):
    """update existing or create new plants if no id is supplied, a new plant is created
    having the supplied attributes (only plant_name is mandatory, others may be
    provided)"""
    plants_modified = data.PlantsCollection

    # update plants
    plants_saved = await update_plants_from_list_of_dicts(
        plants_modified, plant_dal=plant_dal, taxon_dal=taxon_dal
    )

    logger.info(message := f"Saved updates for {len(plants_modified)} plants.")
    results = {
        "action": "Saved Plants",
        "resource": MajorResource.PLANT,
        "message": get_message(message),
        "plants": plants_saved,
    }  # return the updated/created plants

    return results


@router.delete("/{plant_id}", response_model=BConfirmation)
async def delete_plant(
    plant: Plant = Depends(valid_plant), plant_dal: PlantDAL = Depends(get_plant_dal)
):
    """Tag deleted plant as 'deleted' in database."""
    await plant_dal.delete(plant)

    logger.info(message := f"Deleted plant {plant.plant_name}")
    results = {
        "action": "Deleted plant",
        "message": get_message(
            message, description=f"Plant name: {plant.plant_name}\nDeleted: True"
        ),
    }

    return results


@router.put("/", response_model=BConfirmation)
async def rename_plant(
    args: BPlantsRenameRequest,
    plant_dal: PlantDAL = Depends(get_plant_dal),
    history_dal: HistoryDAL = Depends(get_history_dal),
    image_dal: ImageDAL = Depends(get_image_dal),
):
    """We use the put method to rename a plant."""  # todo use id
    plant = await plant_dal.by_id(args.plant_id)
    assert plant.plant_name == args.old_plant_name

    if await plant_dal.exists(args.new_plant_name):
        raise PlantAlreadyExists(args.new_plant_name)

    # rename plant name
    plant.plant_name = args.new_plant_name

    # most difficult task: jpg exif tags use plant name not id; we need to change
    # each plant name occurence
    count_modified_images = await rename_plant_in_image_files(
        plant=plant, plant_name_old=args.old_plant_name, image_dal=image_dal
    )

    await create_history_entry(
        description=f"Renamed to {args.new_plant_name}",
        history_dal=history_dal,
        plant_dal=plant_dal,
        plant_id=plant.id,
        plant_name=args.old_plant_name,
    )

    logger.info(f"Modified {count_modified_images} images.")
    results = {
        "action": "Renamed plant",
        "message": get_message(
            f"Renamed {args.old_plant_name} to {args.new_plant_name}",
            description=f"Modified {count_modified_images} images.",
        ),
    }

    return results


@router.get("/", response_model=BResultsPlants)
async def get_plants(plant_dal: PlantDAL = Depends(get_plant_dal)):
    """Read (almost unfiltered) plants information from db."""
    plants = await fetch_plants(plant_dal=plant_dal)
    results = {
        "action": "Get plants",
        "message": get_message(f"Loaded {len(plants)} plants from database."),
        "PlantsCollection": plants,
    }

    return results


@router.post(
    "/propose_subsequent_plant_name/{original_plant_name}",
    response_model=BResultsProposeSubsequentPlantName,
)
async def propose_subsequent_plant_name(original_plant_name: str):
    """Derive subsequent name for supplied plant name, e.g. "Aloe depressa VI" for "Aloe
    depressa V"."""
    subsequent_plant_name = generate_subsequent_plant_name(original_plant_name)
    return {
        "original_plant_name": original_plant_name,
        "subsequent_plant_name": subsequent_plant_name,
    }

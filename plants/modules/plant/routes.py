from __future__ import annotations

import datetime
import logging
from typing import Any, cast

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
from plants.exceptions import PlantAlreadyExistsError

# if TYPE_CHECKING:
from plants.modules.event.event_dal import EventDAL
from plants.modules.image.image_dal import ImageDAL
from plants.modules.image.services import rename_plant_in_image_files
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.plant.schemas import (
    BResultsPlantCloned,
    BResultsPlants,
    BResultsPlantsUpdate,
    BResultsProposeSubsequentPlantName,
    PlantCreate,
    PlantRenameRequest,
    PlantsUpdateRequest,
    ResultsPlantCreated,
)
from plants.modules.plant.services import (
    create_new_plant,
    deep_clone_plant,
    fetch_plants,
    generate_subsequent_plant_name,
    update_plants_from_list_of_dicts,
)
from plants.modules.taxon.taxon_dal import TaxonDAL
from plants.shared.enums import MajorResource
from plants.shared.history_dal import HistoryDAL
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
) -> Any:
    """clone plant with supplied plant_id; include duplication of events; excludes regular image
    assignments (only to events)"""
    if not plant_name_clone or await plant_dal.exists(plant_name_clone):
        raise PlantAlreadyExistsError(plant_name_clone)

    await deep_clone_plant(
        plant_original,
        plant_name_clone,
        plant_dal=plant_dal,
        event_dal=event_dal,
    )

    plant_clone = await plant_dal.by_name(
        plant_name_clone,
        raise_not_found=True,
    )
    plant_clone = cast(Plant, plant_clone)

    await history_dal.create_entry(
        plant=plant_clone,
        description=f"Cloned from {plant_original.plant_name} ({plant_original.id})",
    )

    logger.info(
        msg := f"Cloned {plant_original.plant_name} ({plant_original.id}) "
        f"into {plant_clone.plant_name} ({plant_clone.id})"
    )

    return {
        "action": "Cloned plant",
        "message": get_message(msg, description=msg),
        "plant": plant_clone,
    }


@router.post("/", response_model=ResultsPlantCreated)
async def create_plant(
    new_plant: PlantCreate,
    plant_dal: PlantDAL = Depends(get_plant_dal),
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
) -> Any:
    """create new plant using the supplied attributes (only plant_name is mandatory, others may be
    provided)"""
    plant_saved = await create_new_plant(new_plant, plant_dal=plant_dal, taxon_dal=taxon_dal)

    logger.info(message := f"Created new plant {plant_saved.id} " f"({plant_saved.plant_name}).")
    return {
        "action": "Saved Plant",
        "resource": MajorResource.PLANT,
        "message": get_message(message),
        "plant": plant_saved,
    }


@router.put("/", response_model=BResultsPlantsUpdate)
async def update_plants(
    data: PlantsUpdateRequest,
    plant_dal: PlantDAL = Depends(get_plant_dal),
    taxon_dal: TaxonDAL = Depends(get_taxon_dal),
) -> Any:
    """Update existing plants."""
    plants_saved = await update_plants_from_list_of_dicts(
        data.PlantsCollection, plant_dal=plant_dal, taxon_dal=taxon_dal
    )

    logger.info(message := f"Saved updates for {len(data.PlantsCollection)} plants.")
    return {
        "action": "Saved Plants",
        "resource": MajorResource.PLANT,
        "message": get_message(message),
        "plants": plants_saved,
    }


@router.delete("/{plant_id}", response_model=BConfirmation)
async def delete_plant(
    plant: Plant = Depends(valid_plant), plant_dal: PlantDAL = Depends(get_plant_dal)
) -> Any:
    """Tag deleted plant as 'deleted' in database."""
    await plant_dal.delete(plant)

    logger.info(message := f"Deleted plant {plant.plant_name}")
    return {
        "action": "Deleted plant",
        "message": get_message(
            message, description=f"Plant name: {plant.plant_name}\nDeleted: True"
        ),
    }


@router.put("/{plant_id}/rename", response_model=BConfirmation)
async def rename_plant(
    args: PlantRenameRequest,
    plant: Plant = Depends(valid_plant),
    plant_dal: PlantDAL = Depends(get_plant_dal),
    history_dal: HistoryDAL = Depends(get_history_dal),
    image_dal: ImageDAL = Depends(get_image_dal),
) -> Any:
    """We use the put method to rename a plant."""
    old_plant_name = plant.plant_name
    if await plant_dal.exists(args.new_plant_name):
        raise PlantAlreadyExistsError(args.new_plant_name)
    plant.plant_name = args.new_plant_name

    # most difficult task: jpg exif tags use plant name not id; we need to change
    # each plant name occurence
    count_modified_images = await rename_plant_in_image_files(
        plant=plant, plant_name_old=old_plant_name, image_dal=image_dal
    )

    await history_dal.create_entry(
        plant=plant, description=f"Renamed {old_plant_name} ({plant.id}) to {args.new_plant_name}"
    )

    logger.info(f"Modified {count_modified_images} images.")
    return {
        "action": "Renamed plant",
        "message": get_message(
            f"Renamed {old_plant_name} to {args.new_plant_name}",
            description=f"Modified {count_modified_images} images.",
        ),
    }


@router.get("/", response_model=BResultsPlants)
async def get_plants(plant_dal: PlantDAL = Depends(get_plant_dal)) -> Any:
    """Read (almost unfiltered) plants information from db."""
    plants = await fetch_plants(plant_dal=plant_dal)
    return {
        "action": "Get plants",
        "message": get_message(f"Loaded {len(plants)} plants from database."),
        "PlantsCollection": plants,
    }


@router.post(
    "/propose_subsequent_plant_name/{original_plant_name}",
    response_model=BResultsProposeSubsequentPlantName,
)
async def propose_subsequent_plant_name(original_plant_name: str) -> Any:
    """Derive subsequent name for supplied plant name, e.g. "Aloe depressa VI" for "Aloe depressa
    V"."""
    subsequent_plant_name = generate_subsequent_plant_name(original_plant_name)
    return {
        "original_plant_name": original_plant_name,
        "subsequent_plant_name": subsequent_plant_name,
    }

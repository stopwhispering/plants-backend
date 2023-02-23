import logging
from collections import defaultdict

from fastapi import APIRouter, Depends

from plants.dependencies import get_event_dal, get_image_dal, get_plant_dal, valid_plant
from plants.modules.event.event_dal import EventDAL
from plants.modules.event.models import Soil
from plants.modules.event.schemas import (
    BPResultsUpdateCreateSoil,
    BResultsEventResource,
    BResultsSoilsResource,
    FRequestCreateOrUpdateEvent,
    SoilCreate,
    SoilUpdate,
)
from plants.modules.event.services import (
    create_or_update_event,
    create_soil,
    fetch_soils,
    read_events_for_plant,
    update_soil,
)
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.shared.enums import BMessageType, FBMajorResource
from plants.shared.message_schemas import BSaveConfirmation
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)

router = APIRouter(
    # prefix="/events",
    tags=["events"],
    responses={404: {"description": "Not found"}},
)


@router.get("/events/soils", response_model=BResultsSoilsResource)
async def get_soils(
    event_dal: EventDAL = Depends(get_event_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
):
    soils = await fetch_soils(event_dal=event_dal, plant_dal=plant_dal)
    return {"SoilsCollection": soils}


@router.post("/events/soils", response_model=BPResultsUpdateCreateSoil)
async def create_new_soil(
    new_soil: SoilCreate, event_dal: EventDAL = Depends(get_event_dal)
):
    """create new soil and return it with (newly assigned) id"""
    soil = await create_soil(soil=new_soil, event_dal=event_dal)

    logger.info(msg := f"Created soil with new ID {soil.id}")
    return {"soil": soil, "message": get_message(msg, message_type=BMessageType.DEBUG)}


@router.put("/events/soils", response_model=BPResultsUpdateCreateSoil)
async def update_existing_soil(
    updated_soil: SoilUpdate, event_dal: EventDAL = Depends(get_event_dal)
):
    """update soil attributes"""
    soil: Soil = await update_soil(soil=updated_soil, event_dal=event_dal)

    logger.info(msg := f"Updated soil with ID {soil.id}")
    return {"soil": soil, "message": get_message(msg, message_type=BMessageType.DEBUG)}


@router.get("/events/{plant_id}", response_model=BResultsEventResource)
async def get_events(
    plant: Plant = Depends(valid_plant), event_dal: EventDAL = Depends(get_event_dal)
):
    """
    returns events from event database table
    """
    events = await read_events_for_plant(plant, event_dal=event_dal)

    logger.info(msg := f"Receiving {len(events)} events for {plant.plant_name}.")
    return {
        "events": events,
        "action": "read events for plant",
        "message": get_message(msg, message_type=BMessageType.DEBUG),
    }


@router.post("/events/", response_model=BSaveConfirmation)
async def create_or_update_events(
    events_request: FRequestCreateOrUpdateEvent,
    event_dal: EventDAL = Depends(get_event_dal),
    image_dal: ImageDAL = Depends(get_image_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
):
    """save n events for n plants in database (add, modify, delete)"""
    # frontend submits a dict with events for those plants where at least one event has been changed, added, or
    # deleted. it does, however, always submit all these plants' events

    # loop at the plants and their events, identify additions, deletions, and updates and save them
    counts = defaultdict(int)
    for plant_id, events in events_request.plants_to_events.items():
        await create_or_update_event(
            plant_id=plant_id,
            events=events,
            counts=counts,
            event_dal=event_dal,
            image_dal=image_dal,
            plant_dal=plant_dal,
        )

    logger.info(
        " Saving Events: "
        + (description := ", ".join([f"{key}: {counts[key]}" for key in counts.keys()]))
    )
    results = {
        "resource": FBMajorResource.EVENT,
        "message": get_message(f"Updated events in database.", description=description),
    }

    return results

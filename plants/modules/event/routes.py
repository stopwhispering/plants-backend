from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends

from plants.dependencies import (
    get_event_dal,
    get_florescence_dal,
    get_image_dal,
    get_plant_dal,
    valid_plant,
)
from plants.modules.event.event_dal import EventDAL
from plants.modules.event.models import Soil
from plants.modules.event.schemas import (
    BPResultsUpdateCreateSoil,
    BResultsEventResource,
    BResultsSoilsResource,
    FRequestCreateOrUpdateEvent,
    PlantFlowerMonthRead,
    PlantFlowerYearRead,
    SoilCreate,
    SoilUpdate,
)
from plants.modules.event.services import (
    EventWriter,
    create_soil,
    fetch_soils,
    read_events_for_plant,
    update_soil,
)
from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.pollination.florescence_dal import FlorescenceDAL
from plants.modules.pollination.flower_history_services import (
    generate_flower_history,
)
from plants.shared.enums import MajorResource, MessageType
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
) -> Any:
    soils = await fetch_soils(event_dal=event_dal, plant_dal=plant_dal)
    return {"SoilsCollection": soils}


@router.post("/events/soils", response_model=BPResultsUpdateCreateSoil)
async def create_new_soil(
    new_soil: SoilCreate, event_dal: EventDAL = Depends(get_event_dal)
) -> Any:
    """Create new soil and return it with (newly assigned) id."""
    soil = await create_soil(soil=new_soil, event_dal=event_dal)

    logger.info(msg := f"Created soil with new ID {soil.id}")
    return {"soil": soil, "message": get_message(msg, message_type=MessageType.DEBUG)}


@router.put("/events/soils", response_model=BPResultsUpdateCreateSoil)
async def update_existing_soil(
    updated_soil: SoilUpdate, event_dal: EventDAL = Depends(get_event_dal)
) -> Any:
    """Update soil attributes."""
    soil: Soil = await update_soil(soil=updated_soil, event_dal=event_dal)

    logger.info(msg := f"Updated soil with ID {soil.id}")
    return {"soil": soil, "message": get_message(msg, message_type=MessageType.DEBUG)}


@router.get("/events/{plant_id}", response_model=BResultsEventResource)
async def get_events(
    plant: Plant = Depends(valid_plant),
    event_dal: EventDAL = Depends(get_event_dal),
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
) -> Any:
    """Returns events from event database table."""
    events = await read_events_for_plant(plant, event_dal=event_dal)
    flower_history_rows = await generate_flower_history(
        florescence_dal=florescence_dal, plant=plant
    )

    # for the plant detail page, we need to convert the flower history yearly rows
    flower_history = []
    for row in flower_history_rows:
        converted_row = PlantFlowerYearRead(
            year=row.year,
            month_01=PlantFlowerMonthRead(flowering_state=row.month_01),
            month_02=PlantFlowerMonthRead(flowering_state=row.month_02),
            month_03=PlantFlowerMonthRead(flowering_state=row.month_03),
            month_04=PlantFlowerMonthRead(flowering_state=row.month_04),
            month_05=PlantFlowerMonthRead(flowering_state=row.month_05),
            month_06=PlantFlowerMonthRead(flowering_state=row.month_06),
            month_07=PlantFlowerMonthRead(flowering_state=row.month_07),
            month_08=PlantFlowerMonthRead(flowering_state=row.month_08),
            month_09=PlantFlowerMonthRead(flowering_state=row.month_09),
            month_10=PlantFlowerMonthRead(flowering_state=row.month_10),
            month_11=PlantFlowerMonthRead(flowering_state=row.month_11),
            month_12=PlantFlowerMonthRead(flowering_state=row.month_12),
        )
        flower_history.append(converted_row)

    logger.info(msg := f"Receiving {len(events)} events for {plant.plant_name}.")
    return {
        "events": events,
        "flower_history": flower_history,
        "action": "Read events for plant",
        "message": get_message(msg, message_type=MessageType.DEBUG),
    }


@router.post("/events/", response_model=BSaveConfirmation)
async def create_or_update_events(
    events_request: FRequestCreateOrUpdateEvent,
    event_dal: EventDAL = Depends(get_event_dal),
    image_dal: ImageDAL = Depends(get_image_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    """save n events for n plants in database (add, modify, delete)"""
    # frontend submits a dict with events for those plants where at least one event has
    # been changed, added, or
    # deleted. it does, however, always submit all these plants' events

    # loop at the plants and their events, identify additions, deletions, and updates
    # and save them
    counts: defaultdict[str, int] = defaultdict(int)
    event_writer = EventWriter(event_dal=event_dal, image_dal=image_dal, plant_dal=plant_dal)
    for plant_id, events in events_request.plants_to_events.items():
        await event_writer.create_or_update_event(
            plant_id=plant_id,
            events=events,
            counts=counts,
        )

    description = ", ".join([f"{key}: {counts[key]}" for key in counts])
    logger.info(f"Saving Events: {description}")
    return {
        "resource": MajorResource.EVENT,
        "message": get_message("Updated events in database.", description=description),
    }

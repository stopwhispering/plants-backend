from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import random
from datetime import datetime
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
    CreateOrUpdateEventRequest,
    CreateOrUpdateSoilResponse,
    GetEventsResponse,
    GetSoilsResponse,
    PlantFlowerMonth,
    PlantFlowerYear,
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
from plants.shared.message_schemas import BackendSaveConfirmation
from plants.shared.message_services import get_message

logger = logging.getLogger(__name__)

router = APIRouter(
    # prefix="/events",
    tags=["events"],
    responses={404: {"description": "Not found"}},
)


@router.get("/events/soils", response_model=GetSoilsResponse)
async def get_soils(
    event_dal: EventDAL = Depends(get_event_dal),
    plant_dal: PlantDAL = Depends(get_plant_dal),
) -> Any:
    soils = await fetch_soils(event_dal=event_dal, plant_dal=plant_dal)
    return {"SoilsCollection": soils}


@router.post("/events/soils", response_model=CreateOrUpdateSoilResponse)
async def create_new_soil(
    new_soil: SoilCreate, event_dal: EventDAL = Depends(get_event_dal)
) -> Any:
    """Create new soil and return it with (newly assigned) id."""
    soil = await create_soil(soil=new_soil, event_dal=event_dal)

    logger.info(msg := f"Created soil with new ID {soil.id}")
    return {"soil": soil, "message": get_message(msg, message_type=MessageType.DEBUG)}


@router.put("/events/soils", response_model=CreateOrUpdateSoilResponse)
async def update_existing_soil(
    updated_soil: SoilUpdate, event_dal: EventDAL = Depends(get_event_dal)
) -> Any:
    """Update soil attributes."""
    soil: Soil = await update_soil(soil=updated_soil, event_dal=event_dal)

    logger.info(msg := f"Updated soil with ID {soil.id}")
    return {"soil": soil, "message": get_message(msg, message_type=MessageType.DEBUG)}


@router.get("/events/{plant_id}", response_model=GetEventsResponse)
async def get_events(
    plant: Plant = Depends(valid_plant),
    event_dal: EventDAL = Depends(get_event_dal),
    florescence_dal: FlorescenceDAL = Depends(get_florescence_dal),
) -> Any:
    """Returns events from event database table."""
    events = await read_events_for_plant(plant, event_dal=event_dal)
    flower_history_rows = await generate_flower_history(
        florescence_dal=florescence_dal, plant=plant, include_inactive_plants=True
    )

    # for the plant detail page, we need to convert the flower history yearly rows
    flower_history = []
    for row in flower_history_rows:
        converted_row = PlantFlowerYear(
            year=int(row.year),
            month_01=PlantFlowerMonth(flowering_state=row.month_01, flowering_probability=None),
            month_02=PlantFlowerMonth(flowering_state=row.month_02, flowering_probability=None),
            month_03=PlantFlowerMonth(flowering_state=row.month_03, flowering_probability=None),
            month_04=PlantFlowerMonth(flowering_state=row.month_04, flowering_probability=None),
            month_05=PlantFlowerMonth(flowering_state=row.month_05, flowering_probability=None),
            month_06=PlantFlowerMonth(flowering_state=row.month_06, flowering_probability=None),
            month_07=PlantFlowerMonth(flowering_state=row.month_07, flowering_probability=None),
            month_08=PlantFlowerMonth(flowering_state=row.month_08, flowering_probability=None),
            month_09=PlantFlowerMonth(flowering_state=row.month_09, flowering_probability=None),
            month_10=PlantFlowerMonth(flowering_state=row.month_10, flowering_probability=None),
            month_11=PlantFlowerMonth(flowering_state=row.month_11, flowering_probability=None),
            month_12=PlantFlowerMonth(flowering_state=row.month_12, flowering_probability=None),
        )
        flower_history.append(converted_row)

    # for current months in current year and all months in upcoming year, we return
    # the flowering probability
    # todo: from model
    # for now, we predict random numbers 0. to 1.
    # get future months in current year
    if flower_history:
        flower_history_current_year = flower_history[-1]
        assert flower_history_current_year.year == datetime.today().year
        for month in range(datetime.today().month+1, 13):
            month_field: PlantFlowerMonth = getattr(flower_history_current_year, f"month_{month:02d}")
            month_field.flowering_probability = round(random.uniform(0, 1), 2)
            month_field.flowering_state = None

    else:
        # if no flower history exists, we create a new one for the current year
        flower_history_current_year = PlantFlowerYear(
            year=datetime.today().year,
            month_01=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_02=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_03=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_04=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_05=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_06=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_07=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_08=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_09=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_10=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_11=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
            month_12=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        )
        flower_history.append(flower_history_current_year)

    next_year_row = PlantFlowerYear(
        year=flower_history_current_year.year + 1,
        month_01=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_02=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_03=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_04=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_05=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_06=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_07=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_08=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_09=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_10=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_11=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
        month_12=PlantFlowerMonth(flowering_state=None, flowering_probability=round(random.uniform(0, 1), 2)),
    )
    flower_history.append(next_year_row)

    logger.info(msg := f"Receiving {len(events)} events for {plant.plant_name}.")
    return {
        "events": events,
        "flower_history": flower_history,
        "action": "Read events for plant",
        "message": get_message(msg, message_type=MessageType.DEBUG),
    }


@router.post("/events/", response_model=BackendSaveConfirmation)
async def create_or_update_events(
    events_request: CreateOrUpdateEventRequest,
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

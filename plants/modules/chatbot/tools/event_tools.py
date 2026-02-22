from __future__ import annotations

from typing import List
import datetime
import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from plants.extensions import orm

RESULTS_LIMIT = 50


logger = logging.getLogger(__name__)


class FindEventsInput(BaseModel):
    """Input for find_plants tool."""
    plant_ids: List[int] | None = Field(default=None, description="Plant ids")
    event_notes_keyword: str | None = Field(default=None, description="Keyword in event notes")


class EventSchema(BaseModel):
    plant_id: int | None
    plant_name: str | None = None
    event_notes: str | None = None
    date: datetime.date | None = None
    soil: str | None = None


class FindEventsOutput(BaseModel):
    status: str
    events: List[EventSchema] = Field(default_factory=list)


@tool(
    args_schema=FindEventsInput,
    description="Find events and JSON. Events might include repottings, diseases, purchases, etc. Max=50."
)
async def find_events(
        plant_ids: List[int] = None,
        event_notes_keyword: str = None,
) -> FindEventsOutput:
    """Find events and return a JSON-serializable dict.

    - plant_id: optional filter by plant id
    - event_notes_keyword: optional substring to search in event_notes (case-insensitive)

    Returns: {status, events}
    """
    from plants.modules.event.event_dal import EventDAL

    # normalize inputs
    plant_ids_clean = [int(plant_id) for plant_id in plant_ids] if plant_ids is not None else None
    keyword_clean = (event_notes_keyword or "").strip() if event_notes_keyword else None

    async with orm.SessionFactory.session_factory() as session:  # type: ignore[attr-defined]
        event_dal = EventDAL(session)
        # Use the DAL method that returns dicts with requested fields
        rows = await event_dal.lookup_events(plant_ids=plant_ids_clean, event_notes_keyword=keyword_clean)  # type: ignore[attr-defined]

    # rows are already dicts like {plant_id, plant_name, event_notes, date, soil}
    events_list: List[EventSchema] = [
        EventSchema(
            plant_id=r.get("plant_id"),
            plant_name=r.get("plant_name"),
            event_notes=r.get("event_notes"),
            date=r.get("date"),
            soil=r.get("soil"),
        )
        for r in rows
    ]

    # enforce results limit
    if RESULTS_LIMIT is not None:
        limited = events_list[:RESULTS_LIMIT]
        status = "limit_exceeded" if len(events_list) > RESULTS_LIMIT else "ok"
    else:
        limited = events_list
        status = "ok"

    logger.info(f"find_events input: plant_ids={plant_ids} event_notes_keyword={event_notes_keyword}")
    output = FindEventsOutput(status=status, events=limited)
    logger.info(f"find_events output: (len={len(output.events)}) {output.model_dump()}")

    return output

from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from plants.extensions import orm


class FindEventsInput(BaseModel):
    """Input for find_plants tool."""
    plant_id: int | None = Field(default=None, description="Optional plant id to filter by")
    event_notes_keyword: str = Field(default=None, description="Optional keyword to search for in event notes")


@tool(args_schema=FindEventsInput)
async def find_events(
        plant_id: int = None,
        event_notes_keyword: str = None,
) -> Dict[str, Any]:
    """Find events and return a JSON-serializable dict.

    - plant_id: optional filter by plant id
    - event_notes_keyword: optional substring to search in event_notes (case-insensitive)

    Returns: {status, events, error}
    """
    from plants.modules.event.event_dal import EventDAL

    RESULTS_LIMIT = 50

    # normalize inputs
    plant_id_clean = int(plant_id) if plant_id is not None else None
    keyword_clean = (event_notes_keyword or "").strip() if event_notes_keyword else None

    async with orm.SessionFactory.session_factory() as session:  # type: ignore[attr-defined]
        event_dal = EventDAL(session)
        # Use the DAL method that returns dicts with requested fields
        rows = await event_dal.lookup_events(plant_id=plant_id_clean, event_notes_keyword=keyword_clean)  # type: ignore[attr-defined]

    # rows are already dicts like {plant_id, plant_name, event_notes, date, soil}
    serialized: List[Dict[str, Any]] = [
        {
            "plant_id": r.get("plant_id"),
            "plant_name": r.get("plant_name"),
            "event_notes": r.get("event_notes"),
            "date": r.get("date"),
            "soil": r.get("soil"),
        }
        for r in rows
    ]

    # enforce results limit
    if RESULTS_LIMIT is not None:
        limited = serialized[:RESULTS_LIMIT]
        status = "limit_exceeded" if len(serialized) > RESULTS_LIMIT else "ok"
    else:
        limited = serialized
        status = "ok"

    print(f"find_events input: plant_id={plant_id} event_notes_keyword={event_notes_keyword}")
    print(f"find_events output: {limited}")

    return {"status": status, "events": limited, "error": None}

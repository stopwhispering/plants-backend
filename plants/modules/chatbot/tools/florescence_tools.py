from __future__ import annotations
import datetime
from typing import Any, Dict, List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from plants.extensions import orm
from plants.modules.pollination.florescence_dal import FlorescenceDAL

RESULTS_LIMIT = 50


class FindFlorescencesInput(BaseModel):
    """Input for find_florescences tool."""
    plant_id: int | None = Field(default=None, description="Optional plant id to filter by")
    max_first_flower_opened_at: datetime.date | None = Field(
        default=None, description="Optional: match florescences that started on or before this date"
    )
    min_last_flower_closed_at: datetime.date | None = Field(
        default=None, description="Optional: match florescences that finished on or after this date"
    )
    include_inactive_plants: bool = Field(default=False, description="Whether to include inactive plants in the results; default: False")


@tool(args_schema=FindFlorescencesInput)
async def find_florescences(
    plant_id: int | None = None,
    max_first_flower_opened_at: datetime.date | None = None,
    min_last_flower_closed_at: datetime.date | None = None,
    include_inactive_plants: bool = False,
) -> Dict[str, Any]:
    """Find florescences and return a JSON-serializable dict.

    - plant_id: optional filter by plant id
    - max_first_flower_opened_at: optional date; match florescences that started on or before this date
    - min_last_flower_closed_at: optional date; match florescences that finished on or after this date
    - include_inactive_plants: whether to include inactive plants in the results
    """
    # Normalize and validate inputs
    # pydantic will have converted strings to date objects where applicable

    async with orm.SessionFactory.session_factory() as session:  # type: ignore[attr-defined]
        florescence_dal = FlorescenceDAL(session)
        florescences = await florescence_dal.get_all_florescences(include_inactive_plants=include_inactive_plants)

    def matches(flo):
        # plant id filter
        if plant_id is not None and flo.plant_id != plant_id:
            return False

        # date filters: florescence period is from first_flower_opened_at till last_flower_closed_at
        # use inflorescence_appeared_at as start if first_flower_opened_at is missing
        # use estimated_last_flower_closed_at if last_flower_closed_at is missing
        if max_first_flower_opened_at is not None:
            max_start_date = flo.first_flower_opened_at or flo.inflorescence_appeared_at
            if max_start_date is not None and max_start_date > max_first_flower_opened_at:
                return False

        if min_last_flower_closed_at is not None:
            min_end_date = flo.last_flower_closed_at or flo.estimated_last_flower_closed_at
            if min_end_date is not None and min_end_date < min_last_flower_closed_at:
                return False

        return True

    filtered = [f for f in florescences if matches(f)]

    serialized: List[Dict[str, Any]] = [
        {
            "plant_id": f.plant_id,
            "plant_name": f.plant.plant_name if f.plant else None,
            "first_flower_opened_at": f.first_flower_opened_at.isoformat() if f.first_flower_opened_at else None,
            "last_flower_closed_at": f.last_flower_closed_at.isoformat() if f.last_flower_closed_at else None,
            "inflorescence_appeared_at": f.inflorescence_appeared_at.isoformat() if f.inflorescence_appeared_at else None,
            "florescence_status": str(f.florescence_status) if f.florescence_status is not None else None,
            "comment": f.comment,
        }
        for f in filtered
    ]

    if RESULTS_LIMIT is not None:
        serialized = serialized[:RESULTS_LIMIT]
        status = "limit_exceeded" if len(filtered) > RESULTS_LIMIT else "ok"
    else:
        status = "ok"

    print(
        f"find_florescences input: plant_id={plant_id} "
        f"max_first_flower_opened_at={max_first_flower_opened_at} "
        f"min_last_flower_closed_at={min_last_flower_closed_at} "
        f"include_inactive={include_inactive_plants}"
    )
    print(f"find_florescences output: {serialized}")

    return {"status": status, "florescences": serialized, "error": None}

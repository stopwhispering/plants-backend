from __future__ import annotations
import datetime
import logging
from typing import List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from plants.extensions import orm
from plants.modules.pollination.florescence_dal import FlorescenceDAL

RESULTS_LIMIT = 50

logger = logging.getLogger(__name__)


class FindFlorescencesInput(BaseModel):
    """Input for find_florescences tool."""
    plant_ids: List[int] | None = Field(default=None, description="Plant ids")
    max_first_flower_opened_at: datetime.date | None = Field(
        default=None, description="Match florescences that started on or before this date"
    )
    min_last_flower_closed_at: datetime.date | None = Field(
        default=None, description="Match florescences that finished on or after this date"
    )
    include_inactive_plants: bool = Field(default=False, description="Include inactive plants")


class FlorescenceSchema(BaseModel):
    plant_id: int
    plant_name: str
    first_flower_opened_at: datetime.date | None = None
    last_flower_closed_at: datetime.date | None = None
    inflorescence_appeared_at: datetime.date | None = None
    florescence_status: str | None = None
    comment: str | None = None


class FindFlorescencesOutput(BaseModel):
    """Output schema for find_florescences tool."""
    status: str
    florescences: List[FlorescenceSchema] = Field(default_factory=list)


@tool(
    args_schema=FindFlorescencesInput,
    description="Find florescences and return JSON."
    )
async def find_florescences(
    plant_ids: List[int] | None = None,
    max_first_flower_opened_at: datetime.date | None = None,
    min_last_flower_closed_at: datetime.date | None = None,
    include_inactive_plants: bool = False,
) -> FindFlorescencesOutput:
    """Find florescences and return a JSON-serializable dict.

    - plant_ids: optional list of plant ids to filter by
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
        if plant_ids is not None and flo.plant_id not in plant_ids:
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

    florescences_list: List[FlorescenceSchema] = [
        FlorescenceSchema(
            plant_id=f.plant_id,
            plant_name=f.plant.plant_name,
            first_flower_opened_at=f.first_flower_opened_at,
            last_flower_closed_at=f.last_flower_closed_at,
            inflorescence_appeared_at=f.inflorescence_appeared_at,
            florescence_status=(str(f.florescence_status) if f.florescence_status is not None else None),
            comment=f.comment,
        )
        for f in filtered
    ]

    if RESULTS_LIMIT is not None:
        limited = florescences_list[:RESULTS_LIMIT]
        status = "limit_exceeded" if len(florescences_list) > RESULTS_LIMIT else "ok"
    else:
        limited = florescences_list
        status = "ok"

    logger.info(
        f"find_florescences input: plant_ids={plant_ids} "
        f"max_first_flower_opened_at={max_first_flower_opened_at} "
        f"min_last_flower_closed_at={min_last_flower_closed_at} "
        f"include_inactive={include_inactive_plants}"
    )
    output = FindFlorescencesOutput(status=status, florescences=limited)
    logger.info(f"find_florescences output: (len={len(output.florescences)}) {output.model_dump()}")

    return output

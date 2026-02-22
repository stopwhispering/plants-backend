from __future__ import annotations
import logging
from typing import List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from plants.extensions import orm
from plants.modules.plant.plant_dal import PlantDAL

logger = logging.getLogger(__name__)


class FindPlantsInput(BaseModel):
    """Tool input schema."""
    plant_id: int | None = Field(default=None, description="Plant ID")
    name: str | None = Field(default=None, description="Vernacular or botanical name")
    nursery_source: str | None = Field(default=None, description="Nursery source")


class RelatedPlant(BaseModel):
    id: int
    plant_name: str


class PlantSchema(BaseModel):
    id: int
    plant_name: str
    botanical_name: str | None = None
    nursery_source: str | None = None
    descendant_plants: List[RelatedPlant] = Field(default_factory=list)
    parent_plant: RelatedPlant | None = None
    parent_plant_pollen: RelatedPlant | None = None


class FindPlantsOutput(BaseModel):
    """Output schema for find_plants tool.
    Note: This is NOT supplied to the agent."""
    plants: List[PlantSchema] = Field(default_factory=list)


@tool(
    args_schema=FindPlantsInput,
    description=(
          "Find plants and returns JSON. Max=50."
      )
)
async def find_plants(
        plant_id: int = None,
        name: str = None,
        nursery_source: str = None,
) -> FindPlantsOutput:
    """Return up to 50 plants matching optional filters.
    - name: either plant_name or the botanical (taxon) name to search for
    - nursery_source: optional filter to only include plants from a specific nursery source
    """
    name_clean = (name or "").strip() if name else None
    nursery_source_clean = (nursery_source or "").strip() if nursery_source else None

    # Run DB access inside the async session/loop.
    async with orm.SessionFactory.session_factory() as session:  # type: ignore[attr-defined]
        plant_dal = PlantDAL(session)
        plants = await plant_dal.get_plants_fuzzy(
            plant_id=plant_id, name=name_clean, nursery_source=nursery_source_clean, limit=50
        )

    output = FindPlantsOutput(
        plants=[
            PlantSchema(
                id=p.id,
                plant_name=p.plant_name,
                botanical_name=p.botanical_name,
                nursery_source=p.nursery_source,
                descendant_plants=[
                    RelatedPlant(id=dp.id, plant_name=dp.plant_name)
                    for dp in p.descendant_plants or []
                ],
                parent_plant=(
                    RelatedPlant(id=p.parent_plant.id, plant_name=p.parent_plant.plant_name)
                    if p.parent_plant is not None else None
                ),
                parent_plant_pollen=(
                    RelatedPlant(id=p.parent_plant_pollen.id, plant_name=p.parent_plant_pollen.plant_name)
                    if p.parent_plant_pollen is not None else None
                ),
            )
            for p in plants
        ]
    )

    logger.info(f"find_plants input: plant_id='{plant_id}' name='{name}' nursery_source='{nursery_source}'")
    logger.info(f"find_plants output: (len={len(output.plants)}) {output.model_dump()}")
    return output

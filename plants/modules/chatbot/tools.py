from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool, BaseTool
from pydantic import BaseModel, Field

from plants.extensions import orm
from plants.modules.plant.plant_dal import PlantDAL


class FindPlantsInput(BaseModel):
    """Input for find_plants tool."""
    name: str = Field(description="Optional Vernacular or Botanical Name")
    nursery_source: str = Field(default=None, description="Optional nursery source to filter by")
    include_inactive: bool = Field(default=False, description="Whether to include inactive plants in the results")


@tool(args_schema=FindPlantsInput)
async def find_plants(
        name: str = None,
        nursery_source: str = None,
        include_inactive: bool = False
) -> Dict[str, Any]:
    """Find plants by botanical name and return a JSON-serializable dict.

    - name: either the plant's vernacular name or the botanical (taxon) name to search for
    - nursery_source: optional filter to only include plants from a specific nursery source
    - include_inactive: whether to include inactive plants in the results (optional, default False)
    """
    name_clean = (name or "").strip() if name else None
    # if not name_clean:
    #     return {"status": "error", "plants": [], "error": {"code": "ValidationError", "message": "botanical_name is required"}}
    nursery_source_clean = (nursery_source or "").strip() if nursery_source else None

    # Run the DB access inside the async session/loop where this function runs.
    async with orm.SessionFactory.session_factory() as session:  # type: ignore[attr-defined]
        plant_dal = PlantDAL(session)
        plants = await plant_dal.get_plants_fuzzy(
            name=name_clean, nursery_source=nursery_source_clean, limit=50, include_inactive=include_inactive
        )

    serialized: List[Dict[str, Any]] = [
        {
            "id": p.id,
            "plant_name": p.plant_name,
            "botanical_name": p.botanical_name,
            # "full_botanical_html_name": p.full_botanical_html_name,
            # "taxon_id": p.taxon_id,
            "preview_image_id": p.preview_image_id,
            "nursery_source": p.nursery_source,
        }
        for p in plants
    ]

    print(f"find_plants input: name='{name}' nursery_source='{nursery_source}' include_inactive={include_inactive}")
    print(f"find_plants output: {serialized}")

    return {"status": "ok", "plants": serialized, "error": None}


def get_langchain_tools() -> list[BaseTool]:
    """Return a list of LangChain tools."""
    # async tools are returned as-is; callers/agents should support async tools or wrap them as needed
    return [find_plants]

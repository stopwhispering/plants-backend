from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool, BaseTool
from pydantic import BaseModel, Field

from plants.extensions import orm
from plants.modules.plant.plant_dal import PlantDAL


class FindPlantsByBotanicalNameInput(BaseModel):
    """Input for find_plants_by_botanical_name tool.
    - botanical_name: the botanical (taxon) name to search for (required)
    - include_inactive: whether to include inactive plants in the results (optional, default False)"""
    botanical_name: str = Field(description="Botanical Name")
    include_inactive: bool = Field(default=False, description="Whether to include inactive plants in the results")


@tool(args_schema=FindPlantsByBotanicalNameInput)
async def find_plants_by_botanical_name(
        botanical_name: str,
        include_inactive: bool = False
) -> Dict[str, Any]:
    """Asynchronously find plants by botanical name and return a JSON-serializable dict.

    This version is a plain async function (no sync-to-async bridging). Callers that
    need a sync wrapper should handle that at a higher level.
    """
    botanical_name_clean = (botanical_name or "").strip()
    if not botanical_name_clean:
        return {"status": "error", "plants": [], "error": {"code": "ValidationError", "message": "botanical_name is required"}}

    # Run the DB access inside the async session/loop where this function runs.
    async with orm.SessionFactory.session_factory() as session:  # type: ignore[attr-defined]
        plant_dal = PlantDAL(session)
        plants = await plant_dal.get_plants_by_botanical_name(
            botanical_name_clean, limit=50, include_inactive=include_inactive
        )

    serialized: List[Dict[str, Any]] = [
        {
            "id": p.id,
            "plant_name": p.plant_name,
            "botanical_name": p.botanical_name,
            # "full_botanical_html_name": p.full_botanical_html_name,
            # "taxon_id": p.taxon_id,
            "preview_image_id": p.preview_image_id,
        }
        for p in plants
    ]

    print(f"find_plants_by_botanical_name: found {len(serialized)} plants for botanical_name='{botanical_name_clean}' include_inactive={include_inactive}")
    return {"status": "ok", "plants": serialized, "error": None}


# class WeatherInput(BaseModel):
#     """Input for weather queries."""
#     location: str = Field(description="City name")
#
# @tool(args_schema=WeatherInput)
# def get_weather(location: str) -> str:
#     """Get current weather and optional forecast."""
#     result = f"Current weather in {location}: 12 degrees celsius."
#     return result


def get_langchain_tools() -> list[BaseTool]:
    """Return a list of LangChain tools."""
    # async tools are returned as-is; callers/agents should support async tools or wrap them as needed
    return [find_plants_by_botanical_name]

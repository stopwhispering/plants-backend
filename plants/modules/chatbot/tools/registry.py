from __future__ import annotations

from typing import List
from langchain_core.tools import BaseTool

from .event_tools import find_events
from .florescence_tools import find_florescences
from .plant_tools import find_plants


def get_langchain_tools() -> List[BaseTool]:
    """Return LangChain tools"""
    return [find_plants, find_florescences, find_events]

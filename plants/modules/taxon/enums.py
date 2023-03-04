from __future__ import annotations

from enum import Enum


class BSearchResultSource(Enum):
    SOURCE_PLANTS_DB = "Local DB"
    SOURCE_IPNI = "Plants of the World"
    SOURCE_IPNI_POWO = "International Plant Names Index + Plants of the World"


class FBRank(str, Enum):
    GENUS = "gen."
    SPECIES = "spec."
    SUBSPECIES = "subsp."
    VARIETY = "var."
    FORMA = "forma"

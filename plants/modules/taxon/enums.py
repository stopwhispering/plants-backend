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


class Establishment(str, Enum):
    NATIVE = "Native"
    INTRODUCED = "Introduced"

    @classmethod
    def get_names(cls) -> list[str]:
        return [name for name, value in vars(cls).items() if type(value) is cls]

from enum import Enum


class FBShapeTop(str, Enum):
    SQUARE = "square"
    ROUND = "round"
    OVAL = "oval"
    HEXAGONAL = "hexagonal"


class FBShapeSide(str, Enum):
    VERY_FLAT = "very flat"
    FLAT = "flat"
    HIGH = "high"
    VERY_HIGH = "very high"
    UNKNOWN = "unknown"  # only for legacy data


class PotMaterial(str, Enum):
    PLASTIC = "Plastik"
    TERRACOTTA = "Terrakotta"
    CLAY = "Ton"

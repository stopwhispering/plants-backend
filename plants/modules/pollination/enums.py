from __future__ import annotations

import enum
from enum import Enum


class BFloweringState(Enum):
    """state of flowering"""
    INFLORESCENCE_GROWING = 'inflorescence_growing'
    FLOWERING = 'flowering'
    SEEDS_RIPENING = 'seeds_ripening'
    NOT_FLOWERING = 'not_flowering'


# keep in sync with formatter.js in frontend
class PollinationStatus(str, enum.Enum):
    ATTEMPT = "attempt"
    SEED_CAPSULE = "seed_capsule"
    SEED = "seed"
    GERMINATED = "germinated"
    UNKNOWN = "unknown"
    SELF_POLLINATED = "self_pollinated"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class PollenType(str, enum.Enum):
    FRESH = "fresh"
    FROZEN = "frozen"
    UNKNOWN = "unknown"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class Context(str, enum.Enum):
    IMPORT = "import"
    MANUAL = "manual"  # manual db corrections
    API = "api"  # api calls from frontend


class Location(str, enum.Enum):
    UNKNOWN = "unknown"
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    INDOOR_LED = "indoor_led"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


COLORS_MAP: dict[str, str] = {
    '#f2f600': 'yellow',
    '#d21d26': 'red',
    '#ffffff': 'white',
    '#f5bfd9': 'pale rose',
    '#9a5abf': 'purple',
    '#008b3c': 'green',
    '#ff7c09': 'orange',
    '#16161b': 'black',
    '#909090': 'gray',
    '#6b492b': 'brown',
    '#104e8b': 'dark blue',
    '#b0e2ff': 'light blue',
    '#46f953': 'neon green',
}
COLORS_MAP_TO_RGB = {v: k for k, v in COLORS_MAP.items()}


class FlorescenceStatus(str, enum.Enum):
    INFLORESCENCE_APPEARED = "inflorescence_appeared"
    FLOWERING = "flowering"
    FINISHED = "finished"  # as soon as the last flower is closed
    ABORTED = "aborted"  # not made it to flowering

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    @classmethod
    def get_names(cls) -> list[str]:
        return [name for name, value in vars(cls).items() if type(value) is cls]


class FlowerColorDifferentiation(str, enum.Enum):
    TOP_BOTTOM = "top_bottom"
    OVARY_MOUTH = "ovary_mouth"
    STRIPED = "striped"
    UNIFORM = "uniform"


class StigmaPosition(str, enum.Enum):
    EXSERTED = "exserted"
    MOUTH = "mouth"
    INSERTED = "inserted"
    DEEPLY_INSERTED = "deeply_inserted"


class PollenQuality(str, Enum):
    GOOD = 'good'
    BAD = 'bad'
    UNKNOWN = 'unknown'

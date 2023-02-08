from enum import Enum
from typing import Optional

from pydantic import validator, Extra, constr
from pydantic.main import BaseModel

from decimal import Decimal
from plants.shared.message_schemas import BMessage
from plants.constants import REGEX_DATE


####################################################################################################
# Entities used in both API Requests from Frontend and Responses from Backend (FB...)
####################################################################################################
class FBShapeTop(str, Enum):
    SQUARE = 'square'
    ROUND = 'round'
    OVAL = 'oval'
    HEXAGONAL = 'hexagonal'


class FBShapeSide(str, Enum):
    VERY_FLAT = 'very flat'
    FLAT = 'flat'
    HIGH = 'high'
    VERY_HIGH = 'very high'


class FBImageAssignedToEvent(BaseModel):
    id: int
    filename: constr(min_length=1, max_length=150)

    class Config:
        extra = Extra.forbid
        orm_mode = True
        allow_population_by_field_name = True


####################################################################################################
# Entities used only in API Requests from Frontend (F...)
####################################################################################################
class FSoil(BaseModel):
    id: int
    soil_name: constr(min_length=1, max_length=100, strip_whitespace=True)
    mix: str | None
    description: str | None

    class Config:
        orm_mode = True


class FPot(BaseModel):
    id: Optional[int]  # missing if new  # todo remove id
    material: constr(min_length=1, max_length=50)  # todo enum?
    shape_top: FBShapeTop
    shape_side: FBShapeSide
    diameter_width: Decimal

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class FObservation(BaseModel):
    id: int | None
    diseases: str | None
    stem_max_diameter: Decimal | None
    height: Decimal | None
    observation_notes: str | None

    class Config:
        extra = Extra.forbid


class FEvent(BaseModel):
    id: int
    plant_id: int
    date: str
    event_notes: str | None
    observation: FObservation | None
    soil: FSoil | None
    pot: FPot | None
    images: Optional[list[FBImageAssignedToEvent]]

    class Config:
        extra = Extra.forbid


class FSoilCreate(FSoil):
    id: Optional[int]

    @validator('id')
    def id_must_be_none(cls, id_):  # noqa
        if id_ is not None:
            raise ValueError
        return id_


class FImageDelete(BaseModel):
    id: int
    filename: constr(min_length=1, max_length=150)

    class Config:
        extra = Extra.forbid


class FImagesToDelete(BaseModel):
    images: list[FImageDelete]

    class Config:
        extra = Extra.forbid


class FCreateOrUpdateEvent(FEvent):
    id: Optional[int]  # empty for new, filled for updated events
    date: constr(regex=REGEX_DATE)  # string yyyy-mm-dd
    event_notes: constr(strip_whitespace=True) | None
    images: list[FBImageAssignedToEvent]
    observation: FObservation | None
    soil: FSoil | None
    pot: FPot | None

    class Config:
        extra = Extra.forbid  # todo works?


class FRequestCreateOrUpdateEvent(BaseModel):
    plants_to_events: dict[int, list[FCreateOrUpdateEvent]]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API Responses from Backend (B...)
####################################################################################################
class BSoil(BaseModel):
    id: int
    soil_name: str
    mix: str | None
    description: str | None

    class Config:
        orm_mode = True
        extra = Extra.ignore


class BPot(BaseModel):
    id: Optional[int]  # missing if new  # todo remove id
    material: str
    shape_top: FBShapeTop
    shape_side: FBShapeSide
    diameter_width: Decimal

    class Config:
        extra = Extra.forbid
        use_enum_values = True
        orm_mode = True


class BObservation(BaseModel):
    id: int | None
    diseases: str | None
    stem_max_diameter: Decimal | None
    height: Decimal | None
    observation_notes: str | None

    class Config:
        extra = Extra.forbid
        orm_mode = True


class BEvent(BaseModel):
    id: int
    plant_id: int
    date: str
    event_notes: str | None
    observation: BObservation | None
    soil: BSoil | None
    pot: BPot | None
    images: Optional[list[FBImageAssignedToEvent]]

    class Config:
        extra = Extra.forbid
        orm_mode = True


class BSoilWithCount(BSoil):
    plants_count: int


class BResultsSoilsResource(BaseModel):
    SoilsCollection: list[BSoilWithCount]

    class Config:
        extra = Extra.forbid


class BEvents(BaseModel):
    __root__: list[BEvent]


class BResultsEventResource(BaseModel):
    events: BEvents
    message: BMessage

    class Config:
        extra = Extra.forbid


class BPResultsUpdateCreateSoil(BaseModel):
    soil: BSoil
    message: BMessage

    class Config:
        extra = Extra.forbid

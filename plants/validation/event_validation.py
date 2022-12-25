from enum import Enum
from typing import Optional

from pydantic import validator, Extra, constr
from pydantic.main import BaseModel

from plants.validation.image_validation import FBImage
from plants.validation.message_validation import BMessage


####################################################################################################
# Entities used in both API Requests from Frontend and Responses from Backend (FB...)
####################################################################################################
class FBSoil(BaseModel):
    id: int
    soil_name: str
    mix: str | None
    description: str | None

    class Config:
        orm_mode = True


class FBShapeTop(Enum):
    SQUARE = 'square'
    ROUND = 'round'
    OVAL = 'oval'
    HEXAGONAL = 'hexagonal'


class FBShapeSide(Enum):
    VERY_FLAT = 'very flat'
    FLAT = 'flat'
    HIGH = 'high'
    VERY_HIGH = 'very high'


class FBPot(BaseModel):
    id: Optional[int]  # missing if new  # todo remove id
    material: str
    shape_top: FBShapeTop
    shape_side: FBShapeSide
    diameter_width: float

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class FBObservation(BaseModel):
    id: int | None
    diseases: str | None
    stem_max_diameter: float | None
    height: float | None
    observation_notes: str | None

    class Config:
        extra = Extra.forbid


class FBImageAssignedToEvent(BaseModel):
    id: int  # empty if new # todo really empty?
    filename: str

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True


class FBEvent(BaseModel):
    id: int
    plant_id: int
    date: str
    event_notes: str | None
    observation: Optional[FBObservation]
    soil: Optional[FBSoil]
    pot: Optional[FBPot]
    images: Optional[list[FBImageAssignedToEvent]]

    class Config:
        extra = Extra.forbid


class BPResultsUpdateCreateSoil(BaseModel):
    soil: FBSoil
    message: BMessage

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API Requests from Frontend (F...)
####################################################################################################
class FSoilCreate(FBSoil):
    id: Optional[int]

    @validator('id')
    def id_must_be_none(cls, id_):  # noqa
        if id_ is not None:
            raise ValueError
        return id_


class FImageDelete(BaseModel):
    id: int
    filename: str

    class Config:
        extra = Extra.forbid


class FImagesToDelete(BaseModel):
    images: list[FImageDelete]

    class Config:
        extra = Extra.forbid


class FCreateOrUpdateEvent(FBEvent):
    id: Optional[int]  # empty for new, filled for updated events
    date: constr(regex=r'^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$')  # string yyyy-mm-dd
    event_notes: str | None
    images: list[FBImage]
    observation: FBObservation | None
    soil: FBSoil | None
    pot: FBPot | None

    # class Config:
    #     extra = Extra.forbid  # todo


class FRequestCreateOrUpdateEvent(BaseModel):
    plants_to_events: dict[int, list[FCreateOrUpdateEvent]]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API Responses from Backend (B...)
####################################################################################################
class BSoilWithCount(FBSoil):
    plants_count: int


class BResultsSoilsResource(BaseModel):
    SoilsCollection: list[BSoilWithCount]

    class Config:
        extra = Extra.forbid


class BEvents(BaseModel):
    __root__: list[FBEvent]


class BResultsEventResource(BaseModel):
    events: BEvents
    message: BMessage

    class Config:
        extra = Extra.forbid

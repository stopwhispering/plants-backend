from typing import Optional

from pydantic import validator, Extra, constr
from pydantic.main import BaseModel

from plants.models.enums import ShapeTop, ShapeSide
from plants.validation.message_validation import PMessage


class PRObservation(BaseModel):
    id: int | None
    diseases: str | None
    stem_max_diameter: float | None
    height: float | None
    observation_notes: str | None

    class Config:
        extra = Extra.forbid


class PRPot(BaseModel):
    id: Optional[int]  # missing if new  # todo remove id
    material: str
    shape_top: ShapeTop
    shape_side: ShapeSide
    diameter_width: float

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class PRSoil(BaseModel):
    id: int
    soil_name: str
    mix: str | None
    description: str | None

    class Config:
        orm_mode = True


class PSoilCreate(PRSoil):
    id: Optional[int]

    @validator('id')
    def id_must_be_none(cls, id_):  # noqa
        if id_ is not None:
            raise ValueError
        return id_


class PSoilWithCount(PRSoil):
    plants_count: int


class PImage(BaseModel):
    id: Optional[int]  # empty if new
    filename: str

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True


class PImageDelete(BaseModel):
    id: int
    filename: str

    class Config:
        extra = Extra.forbid


class RImagesToDelete(BaseModel):
    images: list[PImageDelete]

    class Config:
        extra = Extra.forbid


class PEvent(BaseModel):
    id: int
    plant_id: int
    date: str
    event_notes: str | None
    observation: Optional[PRObservation]
    soil: Optional[PRSoil]
    pot: Optional[PRPot]
    images: Optional[list[PImage]]

    class Config:
        extra = Extra.forbid


class PEvents(BaseModel):
    __root__: list[PEvent]


class RCreateOrUpdateEvent(PEvent):
    id: Optional[int]  # empty for new, filled for updated events
    date: constr(regex=r'^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$')  # string yyyy-mm-dd
    event_notes: str | None
    images: list[PImage]
    observation: PRObservation | None
    soil: PRSoil | None
    pot: PRPot | None


    # class Config:
    #     extra = Extra.forbid


class RRequestCreateOrUpdateEvent(BaseModel):
    plants_to_events: dict[int, list[RCreateOrUpdateEvent]]

    class Config:
        extra = Extra.forbid


class PResultsEventResource(BaseModel):
    events: PEvents
    message: PMessage

    class Config:
        extra = Extra.forbid


class PResultsUpdateCreateSoil(BaseModel):
    soil: PRSoil
    message: PMessage

    class Config:
        extra = Extra.forbid


class PResultsSoilsResource(BaseModel):
    SoilsCollection: list[PSoilWithCount]

    class Config:
        extra = Extra.forbid

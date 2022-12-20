from typing import Optional

from pydantic import validator, Extra
from pydantic.main import BaseModel

from plants.models.enums import ShapeTop, ShapeSide
from plants.validation.message_validation import PMessage


class PObservation(BaseModel):
    id: Optional[int]  # empty if new
    diseases: Optional[str]
    stem_max_diameter: Optional[float]  # todo remove?
    height: Optional[float]  # todo remove?
    observation_notes: Optional[str]

    class Config:
        extra = Extra.forbid


class PPot(BaseModel):
    id: Optional[int]  # missing if new
    material: str
    shape_top: ShapeTop
    shape_side: ShapeSide
    diameter_width: Optional[float]

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class PSoil(BaseModel):
    id: int
    soil_name: str
    mix: str
    description: Optional[str]

    class Config:
        # extra = 'forbid'  # plants_count when updated from frontend #todo forbid
        orm_mode = True


class PSoilCreate(PSoil):
    id: Optional[int]

    @validator('id')
    def id_must_be_none(cls, id_):  # noqa
        if id_ is not None:
            raise ValueError
        return id_


class PSoilWithCount(PSoil):
    plants_count: int


class PImage(BaseModel):
    id: Optional[int]  # empty if new
    filename: str

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True


class PImageDelete(BaseModel):
    # id: Optional[int]  # empty if new
    # path_full_local: Path
    filename: str
    # absolute_path: Path = Field(alias='path_full_local')

    class Config:
        extra = Extra.forbid


class PImagesDelete(BaseModel):
    images: list[PImageDelete]

    class Config:
        extra = Extra.forbid


class PEvent(BaseModel):
    id: int
    date: str
    event_notes: str | None
    # observation_id: Optional[int]
    observation: Optional[PObservation]  # why here and as observation.id? the same or differnt???  # todo remove one
    # pot_id: Optional[int]
    # pot_event_type: Optional[str]  # todo enum ('cancel' | 'repot') just like in ts or remove alltogether
    # soil_id: Optional[int]  # why here and as soil.id? the same or differnt???  # todo remove one
    soil: Optional[PSoil]
    # soil_event_type:  Optional[str]  # todo enum ('cancel') just like in ts or remove alltogether
    plant_id: int
    pot: Optional[PPot]
    images: Optional[list[PImage]]

    class Config:
        extra = Extra.forbid


class PEvents(BaseModel):
    __root__: list[PEvent]


class PEventCreateOrUpdate(PEvent):
    id: Optional[int]  # empty for new, filled for updated events


class PEventCreateOrUpdateRequest(BaseModel):
    plants_to_events: dict[int, list[PEventCreateOrUpdate]]

    class Config:
        extra = Extra.forbid


class PResultsEventResource(BaseModel):
    events: PEvents
    message: PMessage

    class Config:
        extra = Extra.forbid


class PResultsUpdateCreateSoil(BaseModel):
    soil: PSoil
    message: PMessage

    class Config:
        extra = Extra.forbid


class PResultsSoilsResource(BaseModel):
    SoilsCollection: list[PSoilWithCount]

    class Config:
        extra = Extra.forbid

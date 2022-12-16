from typing import Optional, List

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
    diameter_width: float

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
    images: List[PImageDelete]

    class Config:
        extra = Extra.forbid


class PEvent(BaseModel):
    id: int
    date: str
    event_notes: Optional[str]
    observation_id: Optional[int]
    observation: Optional[PObservation]
    pot_id: Optional[int]
    pot_event_type: Optional[str]
    soil_id: Optional[int]
    soil: Optional[PSoil]
    soil_event_type: Optional[str]
    plant_id: int
    pot: Optional[PPot]
    images: Optional[List[PImage]]

    class Config:
        extra = Extra.forbid


class PEventCreateOrUpdate(PEvent):
    id: Optional[int]  # empty for new, filled for updated events


class PEventCreateOrUpdateRequest(BaseModel):
    plants_to_events: dict[int, list[PEventCreateOrUpdate]]

    class Config:
        extra = Extra.forbid

# class PEventCreateOrUpdate(BaseModel):
#     id: Optional[int]  # property missing if event is new
#     date: str
#     event_notes: Optional[str]
#     observation_id: Optional[int]
#     observation: Optional[PObservation]
#     pot_id: Optional[int]
#     pot_event_type: Optional[str]
#     soil_id: Optional[int]
#     soil: Optional[PSoil]
#     soil_event_type: Optional[str]
#     plant_id: Optional[int]  # property missing if event is new
#     pot: Optional[PPot]
#     images: Optional[List[PImage]]
#
#     class Config:
#         extra = 'forbid'


class PResultsEventResource(BaseModel):
    events: List[PEvent]
    message: PMessage

    class Config:
        extra = Extra.forbid


class PResultsSoilResource(BaseModel):
    soil: PSoil
    message: PMessage

    class Config:
        extra = Extra.forbid


class PResultsSoilsResource(BaseModel):
    SoilsCollection: List[PSoilWithCount]

    class Config:
        extra = Extra.forbid

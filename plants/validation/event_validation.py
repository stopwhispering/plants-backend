from pathlib import Path
from typing import Optional, List

from pydantic import Field
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
        extra = 'forbid'


class PPot(BaseModel):
    id: Optional[int]  # missing if new
    material: str
    shape_top: ShapeTop
    shape_side: ShapeSide
    diameter_width: float

    class Config:
        extra = 'forbid'
        use_enum_values = True


class PSoil(BaseModel):
    id: Optional[int]
    soil_name: str
    mix: str
    description: Optional[str]
    plants_count: Optional[int]

    class Config:
        extra = 'forbid'


class PImage(BaseModel):
    id: Optional[int]  # empty if new
    # path_thumb: Path
    relative_path_thumb: Path = Field(alias='path_thumb')
    # path_original: Path
    relative_path: Path = Field(alias='path_original')

    class Config:
        extra = 'forbid'
        allow_population_by_field_name = True


class PImageDelete(BaseModel):
    # id: Optional[int]  # empty if new
    # path_full_local: Path
    absolute_path: Path = Field(alias='path_full_local')

    class Config:
        extra = 'allow'


class PImagesDelete(BaseModel):
    images: List[PImageDelete]

    class Config:
        extra = 'forbid'


class PEventNew(BaseModel):
    id: Optional[int]  # property missing if event is new
    date: str
    event_notes: Optional[str]
    observation_id: Optional[int]
    observation: Optional[PObservation]
    pot_id: Optional[int]
    pot_event_type: Optional[str]
    soil_id: Optional[int]
    soil: Optional[PSoil]
    soil_event_type: Optional[str]
    plant_id: Optional[int]  # property missing if event is new
    pot: Optional[PPot]
    images: Optional[List[PImage]]

    class Config:
        extra = 'forbid'


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
        extra = 'forbid'


class PResultsEventResource(BaseModel):
    events: List[PEvent]
    message: PMessage

    class Config:
        extra = 'forbid'


class PResultsSoilResource(BaseModel):
    soil: PSoil
    message: PMessage

    class Config:
        extra = 'forbid'


class PResultsSoilsResource(BaseModel):
    SoilsCollection: List[PSoil]

    class Config:
        extra = 'forbid'

from typing import Optional, List

from pydantic.main import BaseModel

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
    shape_top: str
    shape_side: Optional[str]  # todo enforce
    diameter_width: float

    class Config:
        extra = 'forbid'


class PSoilComponent(BaseModel):
    component_name: str
    portion: int

    class Config:
        extra = 'forbid'


class PSoil(BaseModel):
    Optional[id]: int
    soil_name: str
    components: List[PSoilComponent]

    class Config:
        extra = 'forbid'


class PImage(BaseModel):
    id: Optional[int]  # empty if new
    path_thumb: str
    path_original: str

    class Config:
        extra = 'forbid'


class PImageDelete(BaseModel):
    # id: Optional[int]  # empty if new
    # path_thumb: str
    # path_original: str
    path_full_local: str

    class Config:
        extra = 'allow'


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
    # icon':            None,
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

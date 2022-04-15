from pathlib import Path
from typing import Optional, List, Union
from datetime import datetime, date

from pydantic import Field
from pydantic.main import BaseModel

from plants.models.enums import PropagationType, CancellationReason, TagState
from plants.validation.message_validation import PMessage


class PPlantShort(BaseModel):
    plant_name: str
    id: int
    active: bool

    class Config:
        extra = 'forbid'


class PPlantLatestImage(BaseModel):
    path: Path
    relative_path_thumb: Path = Field(alias='path_thumb')
    date: datetime

    class Config:
        extra = 'forbid'
        allow_population_by_field_name = True


class PPlantCurrentSoil(BaseModel):
    soil_name: str
    date: date

    class Config:
        extra = 'forbid'


class PPlantTag(BaseModel):
    id: Optional[int]  # empty if new
    text: str
    state: TagState
    last_update: Optional[datetime]  # empty if new
    plant_id: int

    class Config:
        extra = 'forbid'
        use_enum_values = True


class PPlant(BaseModel):
    id: Optional[int]  # empty if new
    plant_name: str
    field_number: Optional[str]
    geographic_origin: Optional[str]
    nursery_source: Optional[str]
    propagation_type: Optional[PropagationType]
    active: bool
    cancellation_reason: Optional[CancellationReason]  # only set if active == False
    cancellation_date: Optional[Union[datetime, str]]  # only set if active == False
    generation_notes: Optional[str]  # obsolete?
    parent_plant_id: Optional[int]
    parent_plant_pollen_id: Optional[int]
    plant_notes: Optional[str]
    filename_previewimage: Optional[Path]
    hide: Optional[bool]  # i.e. deleted  todo: enforce True/False
    last_update: Optional[datetime]  # empty if new
    taxon_id: Optional[int]
    parent_plant: Optional[str]
    parent_plant_pollen: Optional[str]
    descendant_plants: List[PPlantShort] = []
    sibling_plants: List[PPlantShort] = []
    same_taxon_plants: List[PPlantShort] = []
    url_preview: Optional[str]
    current_soil: Optional[PPlantCurrentSoil]
    latest_image_record_date: Optional[date]  # actually used?
    latest_image: Optional[PPlantLatestImage]
    botanical_name: Optional[str]
    taxon_authors: Optional[str]
    tags: List[PPlantTag] = []

    class Config:
        extra = 'forbid'
        use_enum_values = True  # populate model with enum values, rather than the raw enum


class PResultsPlants(BaseModel):
    action: str
    resource: str
    message: Optional[PMessage]
    PlantsCollection: List[PPlant]

    class Config:
        extra = 'forbid'


class PPlantsUpdateRequest(BaseModel):
    PlantsCollection: List[PPlant]

    class Config:
        extra = 'forbid'


class PResultsPlantsUpdate(BaseModel):
    action: str
    resource: str
    message: PMessage
    plants: List[PPlant]

    class Config:
        extra = 'forbid'


class PPlantsDeleteRequest(BaseModel):
    plant_id: int

    class Config:
        extra = 'forbid'


class PPlantsRenameRequest(BaseModel):
    OldPlantName: str
    NewPlantName: str

    class Config:
        extra = 'forbid'




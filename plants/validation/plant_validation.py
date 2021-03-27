from typing import Optional, List, Union
from datetime import datetime, date
from pydantic.main import BaseModel

from plants.validation.message_validation import PMessage


class PDescdendantPlant(BaseModel):
    plant_name: str
    id: int

    class Config:
        extra = 'forbid'


class PPlantLatestImage(BaseModel):
    path: str
    path_thumb: str
    date: datetime

    class Config:
        extra = 'forbid'


class PPlantCurrentSoil(BaseModel):
    soil_name: str
    date: date

    class Config:
        extra = 'forbid'


class PPlantTag(BaseModel):
    id: Optional[int]  # empty if new
    plant_name: Optional[str]  # supplied if new
    text: str
    icon: str  # todo redundant?
    state: str  # todo enum?
    last_update: Optional[datetime]  # empty if new
    plant_id: Optional[int]  # not always supplied -> todo redundant?

    class Config:
        extra = 'forbid'


class PPlant(BaseModel):
    id: Optional[int]  # empty if new
    plant_name: str
    field_number: Optional[str]
    geographic_origin: Optional[str]
    nursery_source: Optional[str]
    propagation_type: Optional[str]  # todo enum?
    count: Optional[str]  # e.g. "3+"  # todo remove
    active: Optional[bool]  # todo: enforce True/Force
    cancellation_reason: Optional[str]  # only set if active == False  # todo enum
    cancellation_date: Optional[Union[datetime, str]]  # only set if active == False
    generation_notes: Optional[str]  # obsolete?
    parent_plant_id: Optional[int]
    parent_plant_pollen_id: Optional[int]
    plant_notes: Optional[str]
    filename_previewimage: Optional[str]
    hide: Optional[bool]  # i.e. deleted  todo: enforce True/False
    last_update: Optional[datetime]  # empty if new
    taxon_id: Optional[int]
    parent_plant: Optional[str]
    parent_plant_pollen: Optional[str]
    descendant_plants: Optional[List[PDescdendantPlant]]  # empty if new
    url_preview: Optional[str]
    current_soil: Optional[PPlantCurrentSoil]
    latest_image_record_date: Optional[date]
    latest_image: Optional[PPlantLatestImage]
    botanical_name: Optional[str]
    taxon_authors: Optional[str]
    tags: Optional[List[PPlantTag]]

    class Config:
        extra = 'forbid'


# class PResponsePlant(BaseModel):
#     action: str
#     resource: str
#     message: PMessage
#     plant: PPlant


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
    plant: str  # todo switch to plant_id

    class Config:
        extra = 'forbid'


class PPlantsRenameRequest(BaseModel):
    OldPlantName: str
    NewPlantName: str

    class Config:
        extra = 'forbid'




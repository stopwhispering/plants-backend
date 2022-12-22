from pathlib import Path
from typing import Optional
from datetime import datetime, date

from pydantic import Field, Extra
from pydantic.main import BaseModel

from plants.models.enums import PropagationType, CancellationReason, TagState
from plants.validation.message_validation import PMessage


class PPlantTag(BaseModel):
    id: Optional[int]  # empty if new
    text: str
    state: TagState
    last_update: Optional[datetime]  # empty if new
    plant_id: int

    class Config:
        extra = Extra.forbid
        use_enum_values = True
        orm_mode = True


class PPlantsDeleteRequest(BaseModel):
    plant_id: int

    class Config:
        extra = Extra.forbid


class PPlantsRenameRequest(BaseModel):
    OldPlantName: str
    NewPlantName: str

    class Config:
        extra = Extra.forbid


class PPlantCurrentSoil(BaseModel):
    soil_name: str
    date: date

    class Config:
        extra = Extra.forbid


class PPlantLatestImage(BaseModel):
    relative_path: Path = Field(alias='path')
    record_date_time: datetime = Field(alias='date')

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True
        orm_mode = True


class PAssociatedPlantExtractForPlant(BaseModel):
    id: int
    plant_name: str
    active: bool

    class Config:
        extra = Extra.forbid
        orm_mode = True


class PAssociatedPlantExtractForPlantOptional(BaseModel):
    id: int | None
    plant_name: str | None
    active: bool | None

    class Config:
        extra = Extra.forbid
        orm_mode = True


class PPlant(BaseModel):
    id: int | None  # None for new plants
    plant_name: str
    field_number: str | None
    geographic_origin: str | None
    nursery_source: str | None
    propagation_type: PropagationType | None
    active: bool
    cancellation_reason: CancellationReason | None  # only set if active == False
    cancellation_date: date | None  # only set if active == False
    generation_notes: str | None
    taxon_id: int | None
    taxon_authors: str | None
    botanical_name: str | None

    # parent_plant_id: int | None
    parent_plant: PAssociatedPlantExtractForPlantOptional | None
    # parent_plant_pollen_id: int | None
    parent_plant_pollen: PAssociatedPlantExtractForPlantOptional | None
    plant_notes: str | None
    filename_previewimage: Path | None
    # hide: bool | None  # i.e. deleted
    last_update: datetime | None  # None for new plants

    descendant_plants_all: list[PAssociatedPlantExtractForPlant]
    sibling_plants: list[PAssociatedPlantExtractForPlant]
    same_taxon_plants: list[PAssociatedPlantExtractForPlant]

    url_preview: Path | None  # todo remove?!?!?!?
    current_soil: PPlantCurrentSoil | None
    latest_image: PPlantLatestImage | None
    tags: list[PPlantTag]

    class Config:
        extra = Extra.forbid
        use_enum_values = True  # populate model with enum values, rather than the raw enum
        orm_mode = True
        allow_population_by_field_name = True


class PResultsPlants(BaseModel):
    action: str
    resource: str
    message: PMessage
    PlantsCollection: list[PPlant]

    class Config:
        extra = Extra.forbid


class PPlantsUpdateRequest(BaseModel):
    PlantsCollection: list[PPlant]

    class Config:
        extra = Extra.forbid


class PResultsPlantsUpdate(BaseModel):
    action: str
    resource: str
    message: PMessage
    plants: list[PPlant]

    class Config:
        extra = Extra.forbid

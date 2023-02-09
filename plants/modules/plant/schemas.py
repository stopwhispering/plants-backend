from pathlib import Path
from datetime import datetime, date
from typing import Optional

from pydantic import Field, Extra, constr
from plants.modules.plant.enums import FBPropagationType, FBCancellationReason, TagState
from plants.shared.base_schema import BaseSchema, ResponseContainer, MajorResponseContainer, RequestContainer


class FBPlantTag(BaseSchema):
    id: Optional[int]
    state: TagState
    text: constr(min_length=1, max_length=20)
    last_update: datetime | None
    plant_id: int

    class Config:
        use_enum_values = True


class ShortPlant(BaseSchema):
    id: int
    plant_name: constr(min_length=1, max_length=100)
    active: bool


class PlantCurrentSoil(BaseSchema):
    soil_name: constr(min_length=1, max_length=100)
    date: date


class PlantLatestImage(BaseSchema):
    relative_path: Path = Field(alias='path')  # todo remove alias
    record_date_time: datetime = Field(alias='date')  # todo remove alias

    class Config:
        allow_population_by_field_name = True


class PlantBase(BaseSchema):
    plant_name: constr(min_length=1, max_length=100)
    field_number: constr(min_length=1, max_length=20) | None
    geographic_origin: constr(min_length=1, max_length=100) | None
    nursery_source: constr(min_length=1, max_length=100) | None
    propagation_type: FBPropagationType | None
    active: bool
    cancellation_reason: FBCancellationReason | None
    cancellation_date: date | None
    generation_notes: constr(min_length=1, max_length=250) | None
    taxon_id: int | None

    parent_plant: ShortPlant | None
    parent_plant_pollen: ShortPlant | None
    plant_notes: str | None
    filename_previewimage: Path | None

    tags: list[FBPlantTag]


class PlantRead(PlantBase):
    id: int

    taxon_authors: str | None
    botanical_name: str | None
    full_botanical_html_name: str | None

    created_at: datetime
    last_update: datetime | None

    descendant_plants_all: list[ShortPlant]
    sibling_plants: list[ShortPlant]
    same_taxon_plants: list[ShortPlant]

    current_soil: PlantCurrentSoil | None
    latest_image: PlantLatestImage | None

    class Config:
        use_enum_values = True  # todo remove


class PlantCreateUpdate(PlantBase):
    id: int | None  # None for new plants

    class Config:
        extra = Extra.ignore
        use_enum_values = True  # todo remove


class FPlantsUpdateRequest(RequestContainer):
    PlantsCollection: list[PlantCreateUpdate]


class BPlantsRenameRequest(BaseSchema):
    plant_id: int
    old_plant_name: constr(min_length=1, max_length=100)
    new_plant_name: constr(min_length=1, max_length=100)


class BResultsPlants(ResponseContainer):
    PlantsCollection: list[PlantRead]


class BResultsPlantsUpdate(MajorResponseContainer):
    plants: list[PlantRead]


class BResultsPlantCloned(ResponseContainer):
    plant: PlantRead


class BResultsProposeSubsequentPlantName(BaseSchema):
    original_plant_name: str
    subsequent_plant_name: constr(min_length=1, max_length=100)

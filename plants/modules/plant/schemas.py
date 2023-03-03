from datetime import date, datetime
from pathlib import Path
from typing import Optional

from pydantic import Extra, constr

from plants.modules.plant.enums import FBCancellationReason, FBPropagationType, TagState
from plants.shared.base_schema import (
    BaseSchema,
    MajorResponseContainer,
    RequestContainer,
    ResponseContainer,
)


class FBPlantTag(BaseSchema):
    id: Optional[int]
    state: TagState
    text: constr(min_length=1, max_length=20)  # type: ignore[valid-type]
    last_update: datetime | None
    plant_id: int


class ShortPlant(BaseSchema):
    id: int
    plant_name: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    active: bool


class PlantCurrentSoil(BaseSchema):
    soil_name: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    date: date


class PlantLatestImage(BaseSchema):
    relative_path: Path
    record_date_time: datetime

    class Config:
        allow_population_by_field_name = True


class PlantBase(BaseSchema):
    plant_name: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    field_number: constr(min_length=1, max_length=20) | None  # type: ignore[valid-type]
    geographic_origin: constr(  # type: ignore[valid-type]
        min_length=1, max_length=100
    ) | None
    nursery_source: constr(  # type: ignore[valid-type]
        min_length=1, max_length=100
    ) | None
    propagation_type: FBPropagationType | None
    active: bool
    cancellation_reason: FBCancellationReason | None
    cancellation_date: date | None
    generation_notes: constr(max_length=250) | None  # type: ignore[valid-type]
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


class PlantCreateUpdate(PlantBase):
    id: int | None  # None for new plants

    class Config:
        extra = Extra.ignore


class FPlantsUpdateRequest(RequestContainer):
    PlantsCollection: list[PlantCreateUpdate]


class BPlantsRenameRequest(BaseSchema):
    plant_id: int
    old_plant_name: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    new_plant_name: constr(min_length=1, max_length=100)  # type: ignore[valid-type]


class BResultsPlants(ResponseContainer):
    PlantsCollection: list[PlantRead]


class BResultsPlantsUpdate(MajorResponseContainer):
    plants: list[PlantRead]


class BResultsPlantCloned(ResponseContainer):
    plant: PlantRead


class BResultsProposeSubsequentPlantName(BaseSchema):
    original_plant_name: str
    subsequent_plant_name: constr(  # type: ignore[valid-type]
        min_length=1, max_length=100
    )

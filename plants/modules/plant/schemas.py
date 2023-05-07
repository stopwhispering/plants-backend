from __future__ import annotations

from datetime import date, datetime

from pydantic import types

from plants.modules.plant.enums import FBCancellationReason, FBPropagationType, TagState
from plants.shared.base_schema import (
    BaseSchema,
    MajorResponseContainer,
    RequestContainer,
    ResponseContainer,
)


class FBPlantTag(BaseSchema):
    id: int | None
    state: TagState
    text: types.constr(min_length=1, max_length=20)  # type: ignore[valid-type]
    last_update: datetime | None
    plant_id: int


class ShortPlant(BaseSchema):
    id: int
    plant_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    active: bool


class PlantCurrentSoil(BaseSchema):
    soil_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    date: date


class PlantLatestImage(BaseSchema):
    filename: str
    record_date_time: datetime

    class Config:
        allow_population_by_field_name = True


class PlantBase(BaseSchema):
    plant_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    field_number: types.constr(min_length=1, max_length=20) | None  # type: ignore[valid-type]
    geographic_origin: types.constr(min_length=1, max_length=100) | None  # type: ignore[valid-type]
    nursery_source: types.constr(min_length=1, max_length=100) | None  # type: ignore[valid-type]
    propagation_type: FBPropagationType | None
    active: bool
    cancellation_reason: FBCancellationReason | None
    cancellation_date: date | None
    generation_notes: types.constr(max_length=250) | None  # type: ignore[valid-type]
    taxon_id: int | None

    parent_plant: ShortPlant | None
    parent_plant_pollen: ShortPlant | None
    plant_notes: str | None
    preview_image_id: int | None

    tags: list[FBPlantTag]

    seed_planting_id: int | None


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


class PlantUpdate(PlantBase):
    id: int


class PlantCreate(PlantBase):
    pass


class PlantsUpdateRequest(RequestContainer):
    PlantsCollection: list[PlantUpdate]


class PlantRenameRequest(BaseSchema):
    new_plant_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]


class ResultsPlantsList(ResponseContainer):
    PlantsCollection: list[PlantRead]


class ResultsPlantsUpdate(MajorResponseContainer):
    plants: list[PlantRead]


class ResultsPlantCreated(MajorResponseContainer):
    plant: PlantRead


class ResultsPlantCloned(ResponseContainer):
    plant: PlantRead


class BResultsProposeSubsequentPlantName(BaseSchema):
    original_plant_name: str
    subsequent_plant_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]

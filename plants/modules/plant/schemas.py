from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import ConfigDict, Field

from plants.modules.plant.enums import FBCancellationReason, FBPropagationType, TagState
from plants.shared.base_schema import (
    BaseSchema,
    MajorResponseContainer,
    RequestContainer,
    ResponseContainer,
)


class TagBase(BaseSchema):
    id: int | None = None
    state: TagState
    text: Annotated[str, Field(min_length=1, max_length=20)]
    last_update: datetime | None = None


class PlantTag(TagBase):
    plant_id: int


class TaxonTag(TagBase):
    taxon_id: int


class ShortPlant(BaseSchema):
    id: int
    plant_name: Annotated[str, Field(min_length=1, max_length=1000)]
    active: bool


class PlantCurrentSoil(BaseSchema):
    soil_name: Annotated[str, Field(min_length=1, max_length=100)]
    date: date


class PlantLatestImage(BaseSchema):
    filename: str
    record_date_time: datetime

    model_config = ConfigDict(populate_by_name=True)


class PlantBase(BaseSchema):
    plant_name: Annotated[str, Field(min_length=1, max_length=1000)]
    field_number: Annotated[str, Field(min_length=1, max_length=20)] | None = None
    geographic_origin: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    nursery_source: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    propagation_type: FBPropagationType | None = None
    active: bool
    cancellation_reason: FBCancellationReason | None = None
    cancellation_date: date | None = None
    generation_notes: Annotated[str, Field(max_length=250)] | None = None
    taxon_id: int | None = None

    parent_plant: ShortPlant | None = None
    parent_plant_pollen: ShortPlant | None = None
    plant_notes: str | None = None
    preview_image_id: int | None = None

    tags: list[PlantTag]

    seed_planting_id: int | None = None

    alternative_botanical_name: str | None = None


class PlantRead(PlantBase):
    id: int

    taxon_authors: str | None = None
    botanical_name: str | None = None
    full_botanical_html_name: str | None = None

    created_at: datetime
    last_update: datetime | None = None

    descendant_plants_all: list[ShortPlant]
    sibling_plants: list[ShortPlant]
    same_taxon_plants: list[ShortPlant]

    current_soil: PlantCurrentSoil | None = None
    latest_image: PlantLatestImage | None = None

    taxon_tags: list[TaxonTag]


class PlantUpdate(PlantBase):
    id: int

    taxon_tags: list[TaxonTag]


class PlantCreate(PlantBase):
    pass


class UpdatePlantsRequest(RequestContainer):
    PlantsCollection: list[PlantUpdate]


class PlantRenameRequest(BaseSchema):
    new_plant_name: Annotated[str, Field(min_length=1, max_length=100)]


class GetPlantsResponse(ResponseContainer):
    PlantsCollection: list[PlantRead]


class UpdatePlantsResponse(MajorResponseContainer):
    pass


class CreatePlantResponse(MajorResponseContainer):
    plant: PlantRead


class ClonePlantResponse(ResponseContainer):
    plant: PlantRead


class ProposeSubsequentPlantNameResponse(BaseSchema):
    original_plant_name: str
    subsequent_plant_name: Annotated[str, Field(min_length=1, max_length=100)]

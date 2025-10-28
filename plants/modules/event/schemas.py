from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator

from plants.constants import REGEX_DATE
from plants.modules.event.enums import FBShapeSide, FBShapeTop, PotMaterial
from plants.modules.pollination.enums import FloweringState
from plants.shared.base_schema import BaseSchema, ResponseContainer


class ImageAssignedToEvent(BaseSchema):
    id: int


class SoilBase(BaseSchema):
    id: int
    soil_name: Annotated[str, Field(min_length=1, max_length=100)]
    mix: str
    description: str | None = None


class SoilUpdate(SoilBase):
    pass


class SoilCreate(SoilBase):
    id: int | None = None


class SoilRead(SoilBase):
    pass


class SoilWithCount(SoilBase):
    plants_count: int
    last_usage_datetime_seed_planting: datetime.datetime | None
    last_usage_datetime_repotting: datetime.datetime | None


class PotBase(BaseSchema):
    material: PotMaterial
    shape_top: FBShapeTop
    shape_side: FBShapeSide
    diameter_width: Decimal


class PotCreateUpdate(PotBase):
    id: int | None = None  # missing if new


class PotRead(PotBase):
    id: int


class ObservationBase(BaseSchema):
    diseases: str | None = None
    observation_notes: str | None = None


class ObservationRead(ObservationBase):
    id: int


class ObservationCreateUpdate(ObservationBase):
    id: int | None = None


class EventBase(BaseSchema):
    plant_id: int
    date: Annotated[str, Field(pattern=REGEX_DATE)]
    event_notes: str | None = None
    images: list[ImageAssignedToEvent] | None = None


class EventCreateUpdate(EventBase):
    id: int | None = None  # empty for new, filled for updated events
    observation: ObservationCreateUpdate | None = None
    soil: SoilUpdate | None = None
    pot: PotCreateUpdate | None = None


class EventRead(EventBase):
    id: int
    observation: ObservationRead | None = None
    soil: SoilRead | None = None
    pot: PotRead | None = None


class ImageToDelete(BaseSchema):
    id: int


class DeleteImagesRequest(BaseSchema):
    images: list[ImageToDelete]


class CreateOrUpdateEventRequest(BaseSchema):
    plants_to_events: dict[int, list[EventCreateUpdate]]


class GetSoilsResponse(BaseSchema):
    SoilsCollection: list[SoilWithCount]


class PlantFlowerMonth(BaseSchema):
    flowering_state: FloweringState | None
    flowering_probability: float | None


class PlantFlowerYear(BaseSchema):
    year: int
    month_01: PlantFlowerMonth
    month_02: PlantFlowerMonth
    month_03: PlantFlowerMonth
    month_04: PlantFlowerMonth
    month_05: PlantFlowerMonth
    month_06: PlantFlowerMonth
    month_07: PlantFlowerMonth
    month_08: PlantFlowerMonth
    month_09: PlantFlowerMonth
    month_10: PlantFlowerMonth
    month_11: PlantFlowerMonth
    month_12: PlantFlowerMonth


class GetEventsResponse(ResponseContainer):
    events: list[EventRead]
    flower_history: list[PlantFlowerYear]


class CreateOrUpdateSoilResponse(ResponseContainer):
    soil: SoilRead

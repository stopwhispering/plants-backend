from __future__ import annotations

from decimal import Decimal

from pydantic import types

from plants.constants import REGEX_DATE
from plants.modules.event.enums import FBShapeSide, FBShapeTop, PotMaterial
from plants.modules.pollination.enums import BFloweringState
from plants.shared.base_schema import BaseSchema, ResponseContainer


class ImageAssignedToEvent(BaseSchema):
    id: int
    # filename: types.constr(min_length=1, max_length=150)  # type: ignore[valid-type]


class SoilBase(BaseSchema):
    id: int
    soil_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    mix: str
    description: str | None


class SoilUpdate(SoilBase):
    pass


class SoilCreate(SoilBase):
    id: int | None = None


class SoilRead(SoilBase):
    pass


class SoilWithCountRead(SoilBase):
    plants_count: int


class PotBase(BaseSchema):
    material: PotMaterial
    shape_top: FBShapeTop
    shape_side: FBShapeSide
    diameter_width: Decimal


class PotCreateUpdate(PotBase):
    id: int | None  # missing if new


class PotRead(PotBase):
    id: int


class ObservationBase(BaseSchema):
    diseases: str | None
    stem_max_diameter: Decimal | None
    height: Decimal | None
    observation_notes: str | None


class ObservationRead(ObservationBase):
    id: int


class ObservationCreateUpdate(ObservationBase):
    id: int | None


class EventBase(BaseSchema):
    plant_id: int
    date: types.constr(regex=REGEX_DATE)  # type: ignore[valid-type]
    event_notes: str | None
    images: list[ImageAssignedToEvent] | None


class EventCreateUpdate(EventBase):
    id: int | None  # empty for new, filled for updated events
    observation: ObservationCreateUpdate | None
    soil: SoilUpdate | None
    pot: PotCreateUpdate | None


class EventRead(EventBase):
    id: int
    observation: ObservationRead | None
    soil: SoilRead | None
    pot: PotRead | None


class FImageDelete(BaseSchema):
    id: int


class FImagesToDelete(BaseSchema):
    images: list[FImageDelete]


class FRequestCreateOrUpdateEvent(BaseSchema):
    plants_to_events: dict[int, list[EventCreateUpdate]]


class BResultsSoilsResource(BaseSchema):
    SoilsCollection: list[SoilWithCountRead]


class PlantFlowerMonthRead(BaseSchema):
    flowering_state: BFloweringState


class PlantFlowerYearRead(BaseSchema):
    year: int
    month_01: PlantFlowerMonthRead
    month_02: PlantFlowerMonthRead
    month_03: PlantFlowerMonthRead
    month_04: PlantFlowerMonthRead
    month_05: PlantFlowerMonthRead
    month_06: PlantFlowerMonthRead
    month_07: PlantFlowerMonthRead
    month_08: PlantFlowerMonthRead
    month_09: PlantFlowerMonthRead
    month_10: PlantFlowerMonthRead
    month_11: PlantFlowerMonthRead
    month_12: PlantFlowerMonthRead


class BResultsEventResource(ResponseContainer):
    events: list[EventRead]
    flower_history: list[PlantFlowerYearRead]


class BPResultsUpdateCreateSoil(ResponseContainer):
    soil: SoilRead

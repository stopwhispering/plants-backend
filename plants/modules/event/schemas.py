from typing import Optional

from pydantic import Extra, constr

from decimal import Decimal

from plants.modules.event.enums import FBShapeTop, FBShapeSide
from plants.shared.base_schema import BaseSchema, ResponseContainer
from plants.constants import REGEX_DATE


class FBImageAssignedToEvent(BaseSchema):
    id: int
    filename: constr(min_length=1, max_length=150)


class SoilBase(BaseSchema):
    id: int
    soil_name: constr(min_length=1, max_length=100)
    mix: str | None
    description: str | None


class SoilUpdate(SoilBase):
    id: int


class SoilCreate(SoilBase):
    pass


class SoilRead(SoilBase):
    id: int

    class Config:
        extra = Extra.ignore  # todo required?


class SoilWithCountRead(SoilBase):
    id: int
    plants_count: int


class PotBase(BaseSchema):
    material: constr(min_length=1, max_length=50)  # todo enum?
    shape_top: FBShapeTop
    shape_side: FBShapeSide
    diameter_width: Decimal


class PotCreateUpdate(PotBase):
    id: Optional[int]  # missing if new  # todo remove id

    class Config:
        use_enum_values = True


class PotRead(PotBase):
    id: int

    class Config:
        use_enum_values = True


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
    date: constr(regex=REGEX_DATE)  # string yyyy-mm-dd
    event_notes: str | None
    images: Optional[list[FBImageAssignedToEvent]]


class EventCreateUpdate(EventBase):
    id: Optional[int]  # empty for new, filled for updated events
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
    filename: constr(min_length=1, max_length=150)


class FImagesToDelete(BaseSchema):
    images: list[FImageDelete]


class FRequestCreateOrUpdateEvent(BaseSchema):
    plants_to_events: dict[int, list[EventCreateUpdate]]


class BResultsSoilsResource(BaseSchema):
    SoilsCollection: list[SoilWithCountRead]


class BResultsEventResource(ResponseContainer):
    events: list[EventRead]


class BPResultsUpdateCreateSoil(ResponseContainer):
    soil: SoilRead

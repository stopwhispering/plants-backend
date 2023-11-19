from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import ConfigDict, field_validator, types

from plants.constants import REGEX_DATE
from plants.modules.pollination.enums import (
    BFloweringState,
    FlorescenceStatus,
    FlowerColorDifferentiation,
    Location,
    PollenQuality,
    PollenType,
    PollinationStatus,
    PredictionModel,
    SeedPlantingStatus,
    StigmaPosition,
)
from plants.shared.base_schema import BaseSchema, RequestContainer, ResponseContainer


class PlantEssentials(BaseSchema):
    id: int
    plant_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    full_botanical_html_name: str | None = None


class SeedPlantingBase(BaseSchema):
    status: SeedPlantingStatus
    pollination_id: int
    comment: str | None = None  # optional free text
    sterilized: bool | None = None  # historical data may be None here and below
    soaked: bool | None = None
    covered: bool | None = None
    planted_on: datetime.date
    count_planted: int | None = None
    soil_id: int | None = None


class SeedPlantingCreate(SeedPlantingBase):
    pass


class SeedPlantingRead(SeedPlantingBase):
    id: int
    count_germinated: int | None = None
    germinated_first_on: datetime.date | None

    seed_capsule_plant_name: str  # orm property
    pollen_donor_plant_name: str  # orm property
    soil_name: str  # orm property

    current_germination_days: int | None = None  # model property (not in DB)
    germination_days: int | None = None  # model property (not in DB)
    predicted_germination_probability: int | None = None  # model property (not in DB)
    predicted_germination_days: int | None = None  # model property (not in DB)

    plants: list[PlantEssentials]

    @field_validator("count_germinated", mode="before")
    @classmethod
    def count_germinated_return_zero_if_none(cls, value: int | None) -> int:
        return value if value is not None else 0


class SeedPlantingUpdate(SeedPlantingBase):
    id: int
    count_germinated: int | None = None
    germinated_first_on: datetime.date | None
    abandoned_on: datetime.date | None


class PollenContainerBase(BaseSchema):
    plant_id: int
    count_stored_pollen_containers: int  # mandatory in this case


class PollenContainerRead(PollenContainerBase):
    plant_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    genus: types.constr(min_length=1, max_length=100) | None = None  # type: ignore[valid-type]
    # plants: list[PlantEssentials]


class PollenContainerCreateUpdate(PollenContainerBase):
    pass


class PollinationBase(BaseSchema):
    seed_capsule_plant_id: int
    pollen_donor_plant_id: int
    pollen_type: PollenType  # PollenType (fresh | frozen | unknown)
    pollinated_at: str | None = None  # e.g. '2022-11-16 12:06';  None for old data
    label_color_rgb: (
        str | None
    ) = None  # e.g. '#FFFF00'  # must be existent in COLORS_MAP; None for old
    location: Location
    count_attempted: types.conint(ge=1)  # type: ignore[valid-type]


class PollinationRead(PollinationBase):
    id: int

    seed_capsule_plant_name: str
    pollen_donor_plant_name: str
    location_text: str

    seed_capsule_plant_preview_image_id: int | None = None
    pollen_donor_plant_preview_image_id: int | None = None

    florescence_id: int
    florescence_comment: str | None = None

    # allow None for old data
    count_attempted: types.conint(ge=1) | None = None  # type: ignore[valid-type]
    count_pollinated: types.conint(ge=1) | None = None  # type: ignore[valid-type]
    count_capsules: types.conint(ge=1) | None = None  # type: ignore[valid-type]

    predicted_ripening_days: types.conint(ge=1) | None = None  # type: ignore[valid-type]
    current_ripening_days: types.conint(ge=0) | None = None  # type: ignore[valid-type]

    pollination_status: str
    ongoing: bool
    harvest_date: str | None = None  # e.g. '2022-11-16'
    seed_capsule_length: float | None = None
    seed_capsule_width: float | None = None
    seed_length: float | None = None
    seed_width: float | None = None
    seed_count: int | None = None
    seed_capsule_description: str | None = None
    seed_description: str | None = None
    pollen_quality: PollenQuality

    seed_plantings: list[SeedPlantingRead]


class HistoricalPollinationRead(PollinationRead):
    reverse: bool


class PollinationUpdate(PollinationBase):
    id: int

    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown |
    # self_pollinated )
    pollination_status: PollinationStatus
    ongoing: bool

    count_pollinated: types.conint(ge=1) | None = None  # type: ignore[valid-type]
    count_capsules: types.conint(ge=1) | None = None  # type: ignore[valid-type]

    harvest_date: types.constr(pattern=REGEX_DATE) | None = None  # type: ignore[valid-type]
    seed_capsule_length: float | None = None
    seed_capsule_width: float | None = None
    seed_length: float | None = None
    seed_width: float | None = None
    seed_count: int | None = None
    seed_capsule_description: str | None = None
    seed_description: str | None = None

    model_config = ConfigDict(extra="ignore")


class PollinationCreate(PollinationBase):
    florescence_id: int
    pollen_quality: PollenQuality

    model_config = ConfigDict(extra="ignore")  # some names and texts not to be inserted into DB


class FlorescenceBase(BaseSchema):
    plant_id: int
    florescence_status: FlorescenceStatus
    inflorescence_appeared_at: types.constr(pattern=REGEX_DATE) | None = None  # type: ignore[valid-type]
    comment: str | None = None  # e.g. location if multiple plants in one container


class FlorescenceCreate(FlorescenceBase):
    pass


PerianthLength = (
    types.condecimal(  # type: ignore[valid-type]
        ge=Decimal(0.1), le=Decimal(99.9)
    )
    | None
)


class FlorescenceUpdate(FlorescenceBase):
    id: int
    branches_count: int | None = None
    flowers_count: int | None = None
    self_pollinated: bool | None = None

    perianth_length: PerianthLength
    perianth_diameter: (
        types.condecimal(  # type: ignore[valid-type]
            ge=Decimal(0.1), le=Decimal(9.9)
        )
        | None
    ) = None  # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    flower_color: (
        types.constr(  # type: ignore[valid-type]
            min_length=7, max_length=7, to_lower=True
        )
        | None
    ) = None  # hex color code, e.g. #f2f600
    flower_color_second: (
        types.constr(  # type: ignore[valid-type]
            min_length=7, max_length=7, to_lower=True
        )
        | None
    ) = None  # hex color code, e.g. #f2f600
    # if flower_color_second set
    flower_colors_differentiation: FlowerColorDifferentiation | None = None
    stigma_position: StigmaPosition | None = None

    first_flower_opened_at: types.constr(pattern=REGEX_DATE) | None = None  # type: ignore[valid-type]
    last_flower_closed_at: types.constr(pattern=REGEX_DATE) | None = None  # type: ignore[valid-type]

    model_config = ConfigDict(extra="ignore")


PerianthDiameter = types.condecimal(ge=Decimal(0.1), le=Decimal(9.9)) | None


class FlorescenceRead(FlorescenceBase):
    id: int
    plant_name: str
    plant_preview_image_id: int | None = None
    plant_self_pollinates: bool | None = None
    self_pollinated: bool | None = None
    available_colors_rgb: list[str]  # e.g. ['#FF0000', '#FF00FF']
    branches_count: int | None = None
    flowers_count: int | None = None

    perianth_length: (
        types.condecimal(  # type: ignore[valid-type]
            ge=Decimal(0.1), le=Decimal(99.9)
        )
        | None
    ) = None  # cm; 3 digits, 1 decimal --> 0.1 .. 99.9
    perianth_diameter: PerianthDiameter  # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    # perianth_diameter: (
    #     types.condecimal(
    #         ge=Decimal(0.1), le=Decimal(9.9)
    #     )
    #     | None
    # )  # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    flower_color: (
        types.constr(  # type: ignore[valid-type]
            min_length=7, max_length=7, to_lower=True
        )
        | None
    ) = None  # hex color code, e.g. #f2f600
    flower_color_second: (
        types.constr(min_length=7, max_length=7, to_lower=True) | None
    ) = None  # hex color code, e.g. #f2f600
    # if flower_color_second set
    flower_colors_differentiation: FlowerColorDifferentiation | None = None
    stigma_position: StigmaPosition | None = None

    first_flower_opened_at: types.constr(pattern=REGEX_DATE) | None = None  # type: ignore[valid-type]
    last_flower_closed_at: types.constr(pattern=REGEX_DATE) | None = None  # type: ignore[valid-type]


class BPollinationResultingPlant(BaseSchema):
    plant_id: int
    plant_name: str
    reverse: bool


class BPotentialPollenDonor(BaseSchema):
    plant_id: int
    plant_name: str
    plant_preview_image_id: int | None = None
    pollen_type: str  # PollenType (fresh | frozen | unknown)
    count_stored_pollen_containers: int | None = None  # only relevant for frozen
    already_ongoing_attempt: bool
    # pollen_harvest_month: str | None  # only relevant for frozen
    probability_pollination_to_seed: int | None = None  # None only in error case

    # pollination_attempts: list[BPollinationAttempt]
    pollination_attempts: list[HistoricalPollinationRead]
    # resulting_plants: list[BPollinationResultingPlant]


class BResultsOngoingPollinations(ResponseContainer):
    ongoing_pollination_collection: list[PollinationRead]


class BPollinationStatus(BaseSchema):
    key: str
    text: str


class FRequestPollenContainers(RequestContainer):
    pollen_container_collection: list[PollenContainerCreateUpdate]


class SettingsRead(BaseSchema):
    colors: list[str]  # e.g. ['#FFFF00', '#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#000000']


# class ActiveSeedPlantingsResult(ResponseContainer):
#     active_seed_planting_collection: list[SeedPlantingRead]


class BResultsActiveFlorescences(ResponseContainer):
    active_florescence_collection: list[FlorescenceRead]


class BResultsPotentialPollenDonors(ResponseContainer):
    potential_pollen_donor_collection: list[BPotentialPollenDonor]


class BPlantWoPollenContainer(BaseSchema):
    plant_id: int
    plant_name: str
    genus: str | None = None


class BPlantForNewFlorescence(BaseSchema):
    plant_id: int
    plant_name: str
    genus: str | None = None


class BResultsPlantsForNewFlorescence(BaseSchema):
    plants_for_new_florescence_collection: list[BPlantForNewFlorescence]


class BResultsPollenContainers(BaseSchema):
    pollen_container_collection: list[PollenContainerRead]
    plants_without_pollen_container_collection: list[BPlantWoPollenContainer]


class BResultsRetraining(BaseSchema):
    model: PredictionModel
    estimator: str
    metric_name: str
    metric_value: float


class BResultsRetrainingPollinationToSeedsModel(BResultsRetraining):
    pass


class BResultsRetrainingRipeningDays(BResultsRetraining):
    pass


class BResultsRetrainingGerminationDays(BResultsRetraining):
    pass


class BResultsRetrainingGerminationProbability(BResultsRetraining):
    pass


class FlowerHistoryMonth(BaseSchema):
    month: str  # e.g. '01'
    flowering_state: BFloweringState


class FlowerHistoryYear(BaseSchema):
    year: str
    months: list[FlowerHistoryMonth]


class FlowerHistoryPlant(BaseSchema):
    plant_id: int
    plant_name: str
    years: list[FlowerHistoryYear]


class FlowerHistoryRow(BaseSchema):
    plant_id: int
    plant_name: str
    year: str
    month_01: BFloweringState
    month_02: BFloweringState
    month_03: BFloweringState
    month_04: BFloweringState
    month_05: BFloweringState
    month_06: BFloweringState
    month_07: BFloweringState
    month_08: BFloweringState
    month_09: BFloweringState
    month_10: BFloweringState
    month_11: BFloweringState
    month_12: BFloweringState


class FlowerHistory(ResponseContainer):
    rows: list[FlowerHistoryRow]


class SeedPlantingPlantNameProposal(BaseSchema):
    plant_name_proposal: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]


class NewPlantFromSeedPlantingRequest(BaseSchema):
    plant_name: str

from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import BeforeValidator, ConfigDict, Field, types

from plants.constants import REGEX_DATE
from plants.modules.pollination.enums import (
    FlorescenceStatus,
    FlowerColorDifferentiation,
    FloweringState,
    Location,
    PollenQuality,
    PollenType,
    PollinationStatus,
    PredictionModel,
    SeedPlantingStatus,
    StigmaPosition,
)
from plants.shared.api_utils import format_api_date, format_api_datetime
from plants.shared.base_schema import BaseSchema, RequestContainer, ResponseContainer


class PlantEssentials(BaseSchema):
    id: int
    plant_name: Annotated[str, Field(min_length=1, max_length=1000)]
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

    # @field_validator("count_germinated", mode="before")  # noqa
    # @classmethod
    # def count_germinated_return_zero_if_none(cls, value: int | None) -> int:
    #     return value if value is not None else 0


class SeedPlantingUpdate(SeedPlantingBase):
    id: int
    count_germinated: int | None = None
    germinated_first_on: datetime.date | None = None
    abandoned_on: datetime.date | None = None


class PollenContainerBase(BaseSchema):
    plant_id: int
    count_stored_pollen_containers: int  # mandatory in this case


class PollenContainerRead(PollenContainerBase):
    plant_name: Annotated[str, Field(min_length=1, max_length=100)]
    genus: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    # list of Date objects
    # previous_flower_closing_dates: list[str]  # e.g. ['2022-11-16', '2022-11-17']
    # plants: list[PlantEssentials]


class PollenContainerCreateUpdate(PollenContainerBase):
    pass


class PollinationBase(BaseSchema):
    seed_capsule_plant_id: int
    pollen_donor_plant_id: int
    pollen_type: PollenType  # PollenType (fresh | frozen | unknown)
    # None only legacy data
    # pollinated_at: //set in subclasses
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
    pollinated_at: Annotated[str, BeforeValidator(format_api_datetime)] | None = None

    florescence_id: int
    florescence_comment: str | None = None
    florescence_status: FlorescenceStatus | None = None  # filled later

    # allow None for old data
    count_attempted: types.conint(ge=1) | None = None  # type: ignore[valid-type]
    count_pollinated: types.conint(ge=1) | None = None  # type: ignore[valid-type]
    count_capsules: types.conint(ge=1) | None = None  # type: ignore[valid-type]

    probability_pollination_to_seed: int | None = None  # only relevant for status ATTEMPT
    predicted_ripening_days: types.conint(ge=1) | None = None  # type: ignore[valid-type]
    current_ripening_days: types.conint(ge=0) | None = None  # type: ignore[valid-type]

    pollination_status: str
    ongoing: bool
    # harvest_date: str | None = None  # e.g. '2022-11-16'
    harvest_date: Annotated[str, BeforeValidator(format_api_date)] | None
    seed_capsule_length: float | None = None
    seed_capsule_width: float | None = None
    seed_length: float | None = None
    seed_width: float | None = None
    seed_count: int | None = None
    seed_capsule_description: str | None = None
    seed_description: str | None = None
    pollen_quality: PollenQuality

    seed_plantings: list[SeedPlantingRead]

    # for sorting in frontend, we need the pollination's florescence and get its
    # latest pollination's current_ripening_days
    florescence_min_current_ripening_days: int | None = None


class HistoricalPollination(PollinationRead):
    reverse: bool | None = None


class PollinationUpdate(PollinationBase):
    id: int

    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown |
    # self_pollinated )
    pollination_status: PollinationStatus
    ongoing: bool

    pollinated_at: str | None = None  # e.g. '2022-11-16 13:23:00'
    pollen_quality: PollenQuality

    count_pollinated: types.conint(ge=1) | None = None  # type: ignore[valid-type]
    count_capsules: types.conint(ge=1) | None = None  # type: ignore[valid-type]

    harvest_date: Annotated[str, Field(pattern=REGEX_DATE)] | None = None
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

    pollinated_at: str | None = None  # e.g. '2022-11-16 13:23:00'

    model_config = ConfigDict(extra="ignore")  # some names and texts not to be inserted into DB


class FlorescenceBase(BaseSchema):
    plant_id: int
    florescence_status: FlorescenceStatus
    inflorescence_appeared_at: Annotated[str, Field(pattern=REGEX_DATE)] | None = None
    first_flower_opened_at: Annotated[str, Field(pattern=REGEX_DATE)] | None = None
    comment: str | None = None  # e.g. location if multiple plants in one container


class FlorescenceCreate(FlorescenceBase):
    pass


class FlorescenceUpdate(FlorescenceBase):
    id: int
    branches_count: int | None = None
    flowers_count: int | None = None
    self_pollinated: bool | None = None

    perianth_length: Annotated[float, Field(le=99.9)] | None = None
    perianth_diameter: Annotated[float, Field(le=9.9)] | None = None
    # ) = None  # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    flower_color: Annotated[str, Field(min_length=7, max_length=7)] | None = None
    flower_color_second: Annotated[str, Field(min_length=7, max_length=7)] | None = None
    flower_colors_differentiation: FlowerColorDifferentiation | None = None
    stigma_position: StigmaPosition | None = None

    last_flower_closed_at: Annotated[str, Field(pattern=REGEX_DATE)] | None = None

    model_config = ConfigDict(extra="ignore")


class FlorescenceRead(FlorescenceBase):
    id: int
    plant_name: str
    plant_taxon_name: str | None = None
    plant_preview_image_id: int | None = None
    plant_self_pollinates: bool | None = None
    self_pollinated: bool | None = None
    available_colors_rgb: list[str]  # e.g. ['#FF0000', '#FF00FF']
    branches_count: int | None = None
    flowers_count: int | None = None

    perianth_length: (
        Annotated[
            float,
            Field(
                le=99.9,
            ),
        ]
        | None
    )

    # ) = None  # cm; 3 digits, 1 decimal --> 0.1 .. 99.9
    perianth_diameter: (
        Annotated[
            float,
            Field(
                le=9.9,
            ),
        ]
        | None
    )

    flower_color: Annotated[str, Field(min_length=7, max_length=7)] | None = None
    flower_color_second: Annotated[str, Field(min_length=7, max_length=7)] | None = None
    flower_colors_differentiation: FlowerColorDifferentiation | None = None
    stigma_position: StigmaPosition | None = None

    last_flower_closed_at: Annotated[str, Field(pattern=REGEX_DATE)] | None


class PlantPreview(BaseSchema):
    plant_id: int
    plant_name: Annotated[str, Field(min_length=1, max_length=100)]
    full_botanical_html_name: str | None = None
    plant_taxon_id: int | None = None
    plant_taxon_name: str | None = None
    active: bool

    parent_plant_capsule_id: int | None = None
    parent_plant_capsule_name: str | None = None
    parent_plant_capsule_taxon_id: int | None = None
    parent_plant_capsule_taxon_name: str | None = None
    parent_plant_pollen_id: int | None = None
    parent_plant_pollen_name: str | None = None
    parent_plant_pollen_taxon_id: int | None = None
    parent_plant_pollen_taxon_name: str | None = None


class PotentialPollenDonor(BaseSchema):
    plant_id: int
    plant_name: str
    plant_taxon_id: int
    plant_taxon_name: str
    plant_preview_image_id: int | None = None
    pollen_type: str  # PollenType (fresh | frozen | unknown)
    count_stored_pollen_containers: int | None = None  # only relevant for frozen
    already_ongoing_attempt: bool
    is_same_plant: bool
    is_same_florescence: bool
    # pollen_harvest_month: str | None  # only relevant for frozen
    probability_pollination_to_seed: int | None = None  # None only in error case

    # pollination_attempts: list[BPollinationAttempt]
    pollination_attempts: list[HistoricalPollination]
    # resulting_plants: list[BPollinationResultingPlant]

    previous_flower_closing_dates: list[str] | None  # e.g. ['2022-11-16', '2022-11-17']

    same_parent_taxa_plants: list[
        PlantPreview
    ] = []  # plants with same parent taxa (both capsule and pollen donor)  # noqa: RUF012


class GetPollinationsResponse(ResponseContainer):
    ongoing_pollination_collection: list[PollinationRead]


class CreateUpdatePollenContainersRequest(RequestContainer):
    pollen_container_collection: list[PollenContainerCreateUpdate]


class SettingsRead(BaseSchema):
    colors: list[str]  # e.g. ['#FFFF00', '#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#000000']


# class ActiveSeedPlantingsResult(ResponseContainer):
#     active_seed_planting_collection: list[SeedPlantingRead]


class BResultsActiveFlorescences(ResponseContainer):
    active_florescence_collection: list[FlorescenceRead]


class BResultsPotentialPollenDonors(ResponseContainer):
    potential_pollen_donor_collection: list[PotentialPollenDonor]


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
    notes: str | None = None


class BResultsRetrainingPollinationToSeedsModel(BResultsRetraining):
    pass


class BResultsRetrainingRipeningDays(BResultsRetraining):
    pass


class BResultsRetrainingGerminationDays(BResultsRetraining):
    pass


class BResultsRetrainingGerminationProbability(BResultsRetraining):
    pass


class BResultsRetrainingFlorescenceProbability(BResultsRetraining):
    pass


class FlowerHistoryMonth(BaseSchema):
    month: str  # e.g. '01'
    flowering_state: FloweringState


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
    genus: str
    species: str | None = None
    year: str
    month_01: FloweringState
    month_02: FloweringState
    month_03: FloweringState
    month_04: FloweringState
    month_05: FloweringState
    month_06: FloweringState
    month_07: FloweringState
    month_08: FloweringState
    month_09: FloweringState
    month_10: FloweringState
    month_11: FloweringState
    month_12: FloweringState


class FlowerHistory(ResponseContainer):
    rows: list[FlowerHistoryRow]


class SeedPlantingPlantNameProposal(BaseSchema):
    plant_name_proposal: Annotated[str, Field(min_length=1, max_length=1000)]


class CreatePlantFromSeedPlantingRequest(BaseSchema):
    plant_name: str


class RequestPredictProbabilityPollinationToSeed(BaseSchema):
    florescence_id: int
    pollen_donor_plant_id: int
    pollen_type: PollenType
    pollen_quality: PollenQuality
    count_attempted: int
    pollinated_at_datetime_utc: datetime.datetime  # e.g. '2025-09-14T13:53:00.000Z' for 2025-09-14 15:53 CET


class BResponsePredictProbabilityPollinationToSeed(ResponseContainer):
    probability_pollination_to_seed: int

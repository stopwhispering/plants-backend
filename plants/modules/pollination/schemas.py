from decimal import Decimal

from pydantic import Extra, condecimal, conint, constr

from plants.constants import REGEX_DATE
from plants.modules.pollination.enums import (
    BFloweringState,
    FlorescenceStatus,
    FlowerColorDifferentiation,
    PollenQuality,
    PollenType,
    PollinationStatus,
    StigmaPosition,
)
from plants.shared.base_schema import BaseSchema, RequestContainer, ResponseContainer


class PollenContainerBase(BaseSchema):
    plant_id: int
    # todo remove/ignore for CreateUpdate
    plant_name: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    # todo remove/ignore for CreateUpdate
    genus: constr(min_length=1, max_length=100) | None  # type: ignore[valid-type]
    count_stored_pollen_containers: int  # mandatory in this case


class PollenContainerRead(PollenContainerBase):
    pass


class PollenContainerCreateUpdate(PollenContainerBase):
    pass


class PollinationBase(BaseSchema):
    seed_capsule_plant_id: int
    pollen_donor_plant_id: int
    pollen_type: PollenType  # PollenType (fresh | frozen | unknown)
    pollination_timestamp: str  # e.g. '2022-11-16 12:06'
    label_color_rgb: str  # e.g. '#FFFF00'  # must be existent in COLORS_MAP
    # todo enum  # e.g. 'outside_led'
    location: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    count: conint(ge=1)  # type: ignore[valid-type]


class PollinationRead(PollinationBase):
    id: int

    seed_capsule_plant_name: str
    pollen_donor_plant_name: str
    location_text: str

    count: conint(ge=1) | None  # type: ignore[valid-type]  # allow None for old data

    pollination_status: str
    ongoing: bool
    harvest_date: str | None  # e.g. '2022-11-16'
    seed_capsule_length: float | None
    seed_capsule_width: float | None
    seed_length: float | None
    seed_width: float | None
    seed_count: int | None
    seed_capsule_description: str | None
    seed_description: str | None
    days_until_first_germination: int | None
    first_seeds_sown: int | None
    first_seeds_germinated: int | None
    germination_rate: float | None
    pollen_quality: PollenQuality


class PollinationUpdate(PollinationBase):
    id: int

    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown |
    # self_pollinated )
    pollination_status: PollinationStatus
    ongoing: bool

    harvest_date: constr(regex=REGEX_DATE) | None  # type: ignore[valid-type]
    seed_capsule_length: float | None
    seed_capsule_width: float | None
    seed_length: float | None
    seed_width: float | None
    seed_count: int | None
    seed_capsule_description: str | None
    seed_description: str | None
    days_until_first_germination: int | None
    first_seeds_sown: int | None
    first_seeds_germinated: int | None

    class Config:
        extra = Extra.ignore


class PollinationCreate(PollinationBase):
    florescenceId: int  # noqa: N815  # todo rename
    pollen_quality: PollenQuality

    class Config:
        extra = Extra.ignore  # some names and texts not to be inserted into DB


class FlorescenceBase(BaseSchema):
    plant_id: int
    # FlorescenceStatus (inflorescence_appeared | flowering | finished)
    florescence_status: FlorescenceStatus
    inflorescence_appearance_date: constr(  # type: ignore[valid-type]
        regex=REGEX_DATE
    ) | None
    comment: str | None  # e.g. location if multiple plants in one container


class FlorescenceCreate(FlorescenceBase):
    pass


class FlorescenceUpdate(FlorescenceBase):
    id: int
    branches_count: int | None
    flowers_count: int | None

    perianth_length: condecimal(  # type: ignore[valid-type]
        ge=Decimal(0.1), le=Decimal(99.9)
    ) | None
    perianth_diameter: condecimal(  # type: ignore[valid-type]
        ge=Decimal(0.1), le=Decimal(9.9)
    ) | None  # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    flower_color: constr(  # type: ignore[valid-type]
        min_length=7, max_length=7, to_lower=True
    ) | None  # hex color code, e.g. #f2f600
    flower_color_second: constr(  # type: ignore[valid-type]
        min_length=7, max_length=7, to_lower=True
    ) | None  # hex color code, e.g. #f2f600
    # if flower_color_second set
    flower_colors_differentiation: FlowerColorDifferentiation | None
    stigma_position: StigmaPosition | None

    first_flower_opening_date: constr(  # type: ignore[valid-type]
        regex=REGEX_DATE
    ) | None
    last_flower_closing_date: constr(  # type: ignore[valid-type]
        regex=REGEX_DATE
    ) | None

    class Config:
        extra = Extra.ignore


class FlorescenceRead(FlorescenceBase):
    id: int
    plant_name: str
    available_colors_rgb: list[str]  # e.g. ['#FF0000', '#FF00FF']
    branches_count: int | None
    flowers_count: int | None

    perianth_length: condecimal(  # type: ignore[valid-type]
        ge=Decimal(0.1), le=Decimal(99.9)
    ) | None  # cm; 3 digits, 1 decimal --> 0.1 .. 99.9
    perianth_diameter: condecimal(  # type: ignore[valid-type]
        ge=Decimal(0.1), le=Decimal(9.9)
    ) | None  # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    flower_color: constr(  # type: ignore[valid-type]
        min_length=7, max_length=7, to_lower=True
    ) | None  # hex color code, e.g. #f2f600
    flower_color_second: constr(  # type: ignore[valid-type]
        min_length=7, max_length=7, to_lower=True
    ) | None  # hex color code, e.g. #f2f600
    # if flower_color_second set
    flower_colors_differentiation: FlowerColorDifferentiation | None
    stigma_position: StigmaPosition | None

    first_flower_opening_date: constr(  # type: ignore[valid-type]
        regex=REGEX_DATE
    ) | None
    last_flower_closing_date: constr(  # type: ignore[valid-type]
        regex=REGEX_DATE
    ) | None


class BPollinationAttempt(BaseSchema):
    reverse: bool
    pollination_status: str  # PollinationStatus
    pollination_at: str | None
    harvest_at: str | None
    germination_rate: float | None
    ongoing: bool


class BPollinationResultingPlant(BaseSchema):
    plant_id: int
    plant_name: str
    reverse: bool


class BPotentialPollenDonor(BaseSchema):
    plant_id: int
    plant_name: str
    pollen_type: str  # PollenType (fresh | frozen | unknown)
    count_stored_pollen_containers: int | None  # only relevant for frozen
    already_ongoing_attempt: bool
    # pollen_harvest_month: str | None  # only relevant for frozen
    probability_pollination_to_seed: int | None  # None only in error case

    pollination_attempts: list[BPollinationAttempt]
    resulting_plants: list[BPollinationResultingPlant]


class BResultsOngoingPollinations(ResponseContainer):
    ongoingPollinationCollection: list[PollinationRead]  # noqa: N815  # todo rename


class BPollinationStatus(BaseSchema):
    key: str
    text: str


class FRequestPollenContainers(RequestContainer):
    # todo rename
    pollenContainerCollection: list[PollenContainerCreateUpdate]  # noqa: N815


class SettingsRead(BaseSchema):
    colors: list[
        str
    ]  # e.g. ['#FFFF00', '#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#000000']


class BResultsActiveFlorescences(ResponseContainer):
    activeFlorescenceCollection: list[FlorescenceRead]  # noqa: N815  # todo rename


class BResultsPotentialPollenDonors(ResponseContainer):
    # todo rename
    potentialPollenDonorCollection: list[BPotentialPollenDonor]  # noqa: N815


class BPlantWoPollenContainer(BaseSchema):
    plant_id: int
    plant_name: str
    genus: str | None


class BPlantForNewFlorescence(BaseSchema):
    plant_id: int
    plant_name: str
    genus: str | None


class BResultsPlantsForNewFlorescence(BaseSchema):
    # todo rename
    plantsForNewFlorescenceCollection: list[BPlantForNewFlorescence]  # noqa: N815


class BResultsPollenContainers(BaseSchema):
    pollenContainerCollection: list[PollenContainerRead]  # noqa: N815  # todo rename
    # todo rename
    plantsWithoutPollenContainerCollection: list[BPlantWoPollenContainer]  # noqa: N815


class BResultsRetrainingPollinationToSeedsModel(BaseSchema):
    mean_f1_score: float
    model: str


class BFloweringPeriodState(BaseSchema):
    month: str  # e.g. '2021-01'
    flowering_state: BFloweringState


class BPlantFlowerHistory(BaseSchema):
    plant_id: int
    plant_name: str

    periods: list[BFloweringPeriodState]


class BResultsFlowerHistory(ResponseContainer):
    plants: list[BPlantFlowerHistory]
    months: list[str]

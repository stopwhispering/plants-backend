from enum import Enum
from typing import Optional, List
from decimal import Decimal

from pydantic import Extra, constr, condecimal, conint
from pydantic.main import BaseModel

from plants.modules.pollination.models import PollenType, FlorescenceStatus, PollinationStatus, \
    FlowerColorDifferentiation, StigmaPosition
from plants.shared.message_schemas import BMessage
from plants.constants import REGEX_DATE


####################################################################################################
# Entities used in both API Requests from Frontend and Responses from Backend (FB...)
####################################################################################################
class FBPollenContainer(BaseModel):
    plant_id: int
    plant_name: constr(min_length=1, max_length=100)  # todo remove/ignore for F...
    genus: constr(min_length=1, max_length=100) | None  # todo remove/ignore for F...
    count_stored_pollen_containers: int  # mandatory in this case

    class Config:
        extra = Extra.forbid


class FRequestNewPollination(BaseModel):
    florescenceId: int
    seedCapsulePlantId: int
    # florescencePlantId: int
    pollenDonorPlantId: int
    pollenType: PollenType  # PollenType (fresh | frozen | unknown)
    pollinationTimestamp: str  # e.g. '2022-11-16 12:06'
    labelColorRgb: str  # e.g. '#FFFF00'  # must be existent in COLORS_MAP
    location: constr(min_length=1, max_length=100)  # todo enum  # e.g. 'outside_led'
    count: conint(ge=1)

    class Config:
        extra = Extra.ignore  # some names and texts not to be inserted into DB
        use_enum_values = True


class FRequestEditedPollination(BaseModel):
    id: int
    seed_capsule_plant_id: int
    pollen_donor_plant_id: int

    pollination_timestamp: str | None  # e.g. '2022-11-16 12:06'
    pollen_type: PollenType
    location: constr(min_length=1, max_length=100) | None  # todo enum  # e.g. 'outside_led'
    count: conint(ge=1)
    label_color_rgb: str  # e.g. '#FFFF00'

    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown | self_pollinated )
    pollination_status: PollinationStatus
    ongoing: bool

    harvest_date: constr(regex=REGEX_DATE) | None  # e.g. '2022-11-16'
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
        use_enum_values = True


class FRequestEditedFlorescence(BaseModel):
    id: int  # florescence id
    plant_id: int
    # plant_name: constr(min_length=1, max_length=100)
    florescence_status: FlorescenceStatus  # FlorescenceStatus (inflorescence_appeared | flowering | finished)
    inflorescence_appearance_date: constr(regex=REGEX_DATE) | None  # e.g. '2022-11-16'
    comment: str | None  # e.g. location if multiple plants in one container
    branches_count: int | None
    flowers_count: int | None

    perianth_length: condecimal(ge=Decimal(0.1), le=Decimal(99.9)) | None  # cm; 3 digits, 1 decimal --> 0.1 .. 99.9
    perianth_diameter: condecimal(ge=Decimal(0.1), le=Decimal(9.9)) | None  # cm; 2 digits, 1 decimal --> 0.1 .. 9.9
    flower_color: constr(min_length=7, max_length=7, to_lower=True) | None  # hex color code, e.g. #f2f600
    flower_color_second: constr(min_length=7, max_length=7, to_lower=True) | None  # hex color code, e.g. #f2f600
    flower_colors_differentiation: FlowerColorDifferentiation | None  # if flower_color_second set
    stigma_position: StigmaPosition | None

    first_flower_opening_date: constr(regex=REGEX_DATE) | None  # e.g. '2022-11-16'
    last_flower_closing_date: constr(regex=REGEX_DATE) | None  # e.g. '2022-11-16'

    class Config:
        extra = Extra.ignore
        use_enum_values = True  # todo remove


class FRequestNewFlorescence(BaseModel):
    plant_id: int
    florescence_status: FlorescenceStatus  # (inflorescence_appeared | flowering | finished | aborted)
    inflorescence_appearance_date: constr(regex=REGEX_DATE) | None  # e.g. '2022-11-16'
    comment: constr(max_length=110, strip_whitespace=True) | None

    class Config:
        extra = Extra.forbid
        use_enum_values = True


####################################################################################################
# Entities used only in API Requests from Frontend (F...)
####################################################################################################
class FRequestPollenContainers(BaseModel):
    pollenContainerCollection: list[FBPollenContainer]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API Responses from Backend (B...)
####################################################################################################
class BActiveFlorescence(BaseModel):
    id: int  # florescence id
    plant_id: int
    plant_name: str  # from as_dict
    florescence_status: FlorescenceStatus  # (inflorescence_appeared | flowering | finished)

    inflorescence_appearance_date: str | None  # e.g. '2022-11-16'
    comment: str | None  # max 110 chars, e.g. location if multiple plants in one container
    branches_count: int | None
    flowers_count: int | None

    perianth_length: Decimal | None
    perianth_diameter: Decimal | None
    flower_color: str | None
    flower_color_second: str | None
    flower_colors_differentiation: FlowerColorDifferentiation | None
    stigma_position: StigmaPosition | None

    first_flower_opening_date: str | None  # e.g. '2022-11-16'
    last_flower_closing_date: str | None  # e.g. '2022-11-16'

    available_colors_rgb: list[str]  # e.g. ['#FF0000', '#FF00FF']

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class BOngoingPollination(BaseModel):
    seed_capsule_plant_id: int
    seed_capsule_plant_name: str
    pollen_donor_plant_id: int
    pollen_donor_plant_name: str
    pollination_timestamp: str | None  # e.g. '2022-11-16 12:06'
    pollen_type: str
    location: str | None
    count: int | None
    location_text: str
    label_color_rgb: str  # e.g. '#FFFF00'

    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown | self_pollinated )
    id: int
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

    class Config:
        extra = Extra.forbid


class BPollinationAttempt(BaseModel):
    reverse: bool
    pollination_status: str  # PollinationStatus
    pollination_at: str | None
    harvest_at: str | None
    germination_rate: float | None
    ongoing: bool

    class Config:
        extra = Extra.forbid


class BPollinationResultingPlant(BaseModel):
    plant_id: int
    plant_name: str
    reverse: bool

    class Config:
        extra = Extra.forbid


class BPotentialPollenDonor(BaseModel):

    plant_id: int
    plant_name: str  # from as_dict
    pollen_type: str  # PollenType (fresh | frozen | unknown)
    count_stored_pollen_containers: int | None  # only relevant for frozen
    already_ongoing_attempt: bool
    # pollen_harvest_month: str | None  # only relevant for frozen
    probability_pollination_to_seed: int | None  # None only in error case

    pollination_attempts: list[BPollinationAttempt]
    resulting_plants: list[BPollinationResultingPlant]

    class Config:
        # orm_mode = True
        extra = Extra.forbid


class BResultsOngoingPollinations(BaseModel):
    action: str
    message: Optional[BMessage]
    ongoingPollinationCollection: List[BOngoingPollination]

    class Config:
        extra = Extra.forbid


class BPollinationStatus(BaseModel):
    # PollinationStatus ['attempt', 'seed_capsule', 'seed', 'germinated', 'unknown', 'self_pollinated']
    key: str
    # PollinationStatus ['attempt', 'seed_capsule', 'seed', 'germinated', 'unknown', 'self_pollinated']
    text: str

    class Config:
        extra = Extra.forbid


class BResultsSettings(BaseModel):
    colors: list[str]  # e.g. ['#FFFF00', '#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#00FFFF', '#000000']
    # pollination_status: list[BPollinationStatus]

    class Config:
        extra = Extra.forbid


class BResultsActiveFlorescences(BaseModel):
    action: str
    message: Optional[BMessage]
    activeFlorescenceCollection: List[BActiveFlorescence]

    class Config:
        extra = Extra.forbid


class BResultsPotentialPollenDonors(BaseModel):
    action: str
    message: Optional[BMessage]
    potentialPollenDonorCollection: List[BPotentialPollenDonor]

    class Config:
        extra = Extra.forbid


class BPlantWithoutPollenContainer(BaseModel):
    plant_id: int
    plant_name: str
    genus: str | None

    class Config:
        extra = Extra.forbid


class BPlantForNewFlorescence(BaseModel):
    plant_id: int
    plant_name: str
    genus: str | None

    class Config:
        extra = Extra.forbid


class BResultsPlantsForNewFlorescence(BaseModel):
    plantsForNewFlorescenceCollection: List[BPlantForNewFlorescence]

    class Config:
        extra = Extra.forbid


class BResultsPollenContainers(BaseModel):
    pollenContainerCollection: list[FBPollenContainer]
    plantsWithoutPollenContainerCollection: list[BPlantWithoutPollenContainer]

    class Config:
        extra = Extra.forbid


class BResultsRetrainingPollinationToSeedsModel(BaseModel):
    mean_f1_score: float
    model: str

    class Config:
        extra = Extra.forbid


class BFloweringState(Enum):
    """state of flowering"""
    INFLORESCENCE_GROWING = 'inflorescence_growing'
    FLOWERING = 'flowering'
    SEEDS_RIPENING = 'seeds_ripening'
    NOT_FLOWERING = 'not_flowering'


class BFloweringPeriodState(BaseModel):
    month: str  # e.g. '2021-01'
    flowering_state: BFloweringState

    class Config:
        extra = Extra.forbid
        orm_mode = True
        use_enum_values = True


class BPlantFlowerHistory(BaseModel):

    plant_id: int
    plant_name: str

    periods: list[BFloweringPeriodState]

    class Config:
        extra = Extra.forbid


class BResultsFlowerHistory(BaseModel):
    action: str
    message: BMessage
    plants: list[BPlantFlowerHistory]
    months: list[str]

    class Config:
        extra = Extra.forbid

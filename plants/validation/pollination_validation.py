from typing import Optional, List

from pydantic import Extra
from pydantic.main import BaseModel

from plants.validation.message_validation import PMessage


class PActiveFlorescence(BaseModel):
    id: int  # florescence id
    plant_id: int
    plant_name: str  # from as_dict
    florescence_status: str  # FlorescenceStatus (inflorescence_appeared | flowering | finished)

    inflorescence_appearance_date: str | None  # e.g. '2022-11-16'
    comment: str | None  # e.g. location if multiple plants in one container
    branches_count: int | None
    flowers_count: int | None
    first_flower_opening_date: str | None  # e.g. '2022-11-16'
    last_flower_closing_date: str | None  # e.g. '2022-11-16'

    available_colors_rgb: list[str]  # e.g. ['#FF0000', '#FF00FF']

    class Config:
        extra = Extra.forbid


class POngoingPollination(BaseModel):
    seed_capsule_plant_id: int
    seed_capsule_plant_name: str
    pollen_donor_plant_id: int
    pollen_donor_plant_name: str
    pollination_timestamp: str | None  # e.g. '2022-11-16 12:06'
    pollen_type: str
    location: str | None
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


class PPollinationAttempt(BaseModel):
    reverse: bool
    pollination_status: str  # PollinationStatus
    pollination_at: str | None
    harvest_at: str | None
    germination_rate: float | None
    ongoing: bool

    class Config:
        extra = Extra.forbid


class PPollinationResultingPlant(BaseModel):
    plant_id: int
    plant_name: str
    reverse: bool

    class Config:
        extra = Extra.forbid


class PPotentialPollenDonor(BaseModel):

    plant_id: int
    plant_name: str  # from as_dict
    pollen_type: str  # PollenType (fresh | frozen | unknown)
    count_stored_pollen_containers: int | None  # only relevant for frozen
    already_ongoing_attempt: bool
    # pollen_harvest_month: str | None  # only relevant for frozen
    probability_pollination_to_seed: int | None  # None only in error case

    pollination_attempts: list[PPollinationAttempt]
    resulting_plants: list[PPollinationResultingPlant]

    class Config:
        # orm_mode = True
        extra = Extra.forbid


class PResultsOngoingPollinations(BaseModel):
    action: str
    # resource: str
    message: Optional[PMessage]
    ongoingPollinationCollection: List[POngoingPollination]

    class Config:
        extra = Extra.forbid  # todo works?


class PPollinationStatus(BaseModel):
    # PollinationStatus ['attempt', 'seed_capsule', 'seed', 'germinated', 'unknown', 'self_pollinated']
    key: str
    # PollinationStatus ['attempt', 'seed_capsule', 'seed', 'germinated', 'unknown', 'self_pollinated']
    text: str

    class Config:
        extra = Extra.forbid


class PResultsSettings(BaseModel):
    colors: list[str]  # e.g. ['#FFFF00', '#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#00FFFF', '#000000']
    pollination_status: list[PPollinationStatus]

    class Config:
        extra = Extra.forbid


class PResultsActiveFlorescences(BaseModel):
    action: str
    message: Optional[PMessage]
    activeFlorescenceCollection: List[PActiveFlorescence]

    class Config:
        extra = Extra.forbid  # todo works?


class PResultsPotentialPollenDonors(BaseModel):
    action: str
    # resource: str
    message: Optional[PMessage]
    potentialPollenDonorCollection: List[PPotentialPollenDonor]

    class Config:
        extra = Extra.forbid  # todo works?


class PPollenContainer(BaseModel):
    plant_id: int
    plant_name: str
    genus: str | None
    count_stored_pollen_containers: int  # mandatory in this case

    class Config:
        extra = Extra.forbid


class PPlantWithoutPollenContainer(BaseModel):
    plant_id: int
    plant_name: str
    genus: str | None

    class Config:
        extra = Extra.forbid


class PPlantForNewFlorescence(BaseModel):
    plant_id: int
    plant_name: str
    genus: str | None

    class Config:
        extra = Extra.forbid


class PResultsPlantsForNewFlorescence(BaseModel):
    plantsForNewFlorescenceCollection: List[PPlantForNewFlorescence]

    class Config:
        extra = Extra.forbid


class PResultsPollenContainers(BaseModel):
    pollenContainerCollection: list[PPollenContainer]
    plantsWithoutPollenContainerCollection: list[PPlantWithoutPollenContainer]

    class Config:
        extra = Extra.forbid


class PRequestPollenContainers(BaseModel):
    pollenContainerCollection: list[PPollenContainer]

    class Config:
        extra = Extra.forbid


class PRequestNewPollination(BaseModel):
    florescenceId: int
    seedCapsulePlantId: int
    # florescencePlantId: int
    pollenDonorPlantId: int
    pollenType: str  # PollenType (fresh | frozen | unknown)
    pollinationTimestamp: str  # e.g. '2022-11-16 12:06'
    labelColorRgb: str  # e.g. 'FFFF00'
    location: str  # e.g. 'outside_led'

    class Config:
        extra = Extra.ignore


class PRequestEditedPollination(BaseModel):
    id: int
    seed_capsule_plant_id: int
    pollen_donor_plant_id: int

    pollination_timestamp: str | None  # e.g. '2022-11-16 12:06'
    pollen_type: str
    location: str | None
    label_color_rgb: str  # e.g. '#FFFF00'

    # PollinationStatus ( attempt | seed_capsule | seed | germinated | unknown | self_pollinated )
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

    class Config:
        extra = Extra.ignore


class PRequestEditedFlorescence(BaseModel):
    id: int  # florescence id
    plant_id: int
    plant_name: str
    florescence_status: str  # FlorescenceStatus (inflorescence_appeared | flowering | finished)
    inflorescence_appearance_date: str | None  # e.g. '2022-11-16'
    comment: str | None  # e.g. location if multiple plants in one container
    branches_count: int | None
    flowers_count: int | None
    first_flower_opening_date: str | None  # e.g. '2022-11-16'
    last_flower_closing_date: str | None  # e.g. '2022-11-16'

    class Config:
        extra = Extra.ignore


class PRequestNewFlorescence(BaseModel):
    plant_id: int
    florescence_status: str  # FlorescenceStatus (inflorescence_appeared | flowering | finished)
    inflorescence_appearance_date: str | None  # e.g. '2022-11-16'
    comment: str | None  # max 40 chars

    class Config:
        extra = Extra.forbid  # todo works?

from enum import Enum
from pathlib import Path
from typing import Optional
from datetime import datetime, date

from pydantic import Field, Extra, validator, root_validator, constr
from pydantic.main import BaseModel

from plants.schemas.shared import BMessage, FBMajorResource


####################################################################################################
# Entities used in both API Requests from Frontend and Responses from Backend (FB...)
####################################################################################################
class FBTagState(str, Enum):
    NONE = 'None'
    INDICATION01 = 'Indication01'
    SUCCESS = 'Success'
    INFORMATION = 'Information'
    ERROR = 'Error'
    WARNING = 'Warning'


class FBPlantTag(BaseModel):
    id: Optional[int]
    state: FBTagState
    text: constr(min_length=1, max_length=20, strip_whitespace=True)
    last_update: datetime | None
    plant_id: int

    class Config:
        extra = Extra.forbid
        use_enum_values = True
        orm_mode = True


class FBAssociatedPlantExtractForPlant(BaseModel):
    id: int
    plant_name: constr(min_length=1, max_length=100)
    active: bool

    class Config:
        extra = Extra.forbid
        orm_mode = True


class FBPlantCurrentSoil(BaseModel):
    soil_name: constr(min_length=1, max_length=100, strip_whitespace=True)
    date: date

    class Config:
        extra = Extra.forbid


class FBPlantLatestImage(BaseModel):
    relative_path: Path = Field(alias='path')
    record_date_time: datetime = Field(alias='date')

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True
        orm_mode = True


class FBPropagationType(str, Enum):
    SEED_COLLECTED = 'seed (collected)'
    OFFSET = 'offset'
    ACQUIRED_AS_PLANT = 'acquired as plant'
    BULBIL = 'bulbil'
    HEAD_CUTTING = 'head cutting'
    LEAF_CUTTING = 'leaf cutting'
    SEED_PURCHASED = 'seed (purchased)'
    UNKNOWN = 'unknown'
    NONE = ''


class FBCancellationReason(str, Enum):
    WINTER_DAMAGE = 'Winter Damage'
    DRIEDOUT = 'Dried Out'
    MOULD = 'Mould'
    MITES = 'Mites'
    OTHER_INSECTS = 'Other Insects'
    ABANDONMENT = 'Abandonment'
    GIFT = 'Gift'
    SALE = 'Sale'
    OTHERS = 'Others'
    # NONE = ''


####################################################################################################
# Entities used only in API Requests from Frontend (F...)
####################################################################################################
class FPlant(BaseModel):
    id: int | None  # None for new plants
    plant_name: constr(min_length=1, max_length=100)
    field_number: constr(min_length=1, max_length=20, strip_whitespace=True) | None
    geographic_origin: constr(min_length=1, max_length=100, strip_whitespace=True) | None
    nursery_source: constr(min_length=1, max_length=100, strip_whitespace=True) | None
    propagation_type: FBPropagationType | None
    active: bool
    cancellation_reason: FBCancellationReason | None
    cancellation_date: date | None
    generation_notes: constr(min_length=1, max_length=250, strip_whitespace=True) | None
    taxon_id: int | None
    taxon_authors: str | None  # irrelevant from frontend
    botanical_name: str | None  # irrelevant from frontend
    full_botanical_html_name: str | None  # irrelevant from frontend

    parent_plant: FBAssociatedPlantExtractForPlant | None
    parent_plant_pollen: FBAssociatedPlantExtractForPlant | None
    plant_notes: str | None
    filename_previewimage: Path | None
    last_update: datetime | None  # None for new plants

    descendant_plants_all: list[FBAssociatedPlantExtractForPlant]
    sibling_plants: list[FBAssociatedPlantExtractForPlant]
    same_taxon_plants: list[FBAssociatedPlantExtractForPlant]

    current_soil: FBPlantCurrentSoil | None
    latest_image: FBPlantLatestImage | None
    tags: list[FBPlantTag]

    class Config:
        extra = Extra.forbid
        use_enum_values = True  # populate model with enum values, rather than the raw enum
        orm_mode = True
        allow_population_by_field_name = True


class FPlantsDeleteRequest(BaseModel):
    plant_id: int

    class Config:
        extra = Extra.forbid


class FPlantsUpdateRequest(BaseModel):
    PlantsCollection: list[FPlant]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API Responses from Backend (B...)
####################################################################################################
class BPlant(BaseModel):
    id: int
    plant_name: str
    field_number: str | None
    geographic_origin: str | None
    nursery_source: str | None
    propagation_type: FBPropagationType | None
    active: bool
    cancellation_reason: FBCancellationReason | None
    cancellation_date: date | None
    generation_notes: str | None
    taxon_id: int | None
    taxon_authors: str | None
    botanical_name: str | None
    full_botanical_html_name: str | None

    parent_plant: FBAssociatedPlantExtractForPlant | None
    parent_plant_pollen: FBAssociatedPlantExtractForPlant | None
    plant_notes: str | None
    filename_previewimage: Path | None
    last_update: datetime | None  # None for new plants

    descendant_plants_all: list[FBAssociatedPlantExtractForPlant]
    sibling_plants: list[FBAssociatedPlantExtractForPlant]
    same_taxon_plants: list[FBAssociatedPlantExtractForPlant]

    current_soil: FBPlantCurrentSoil | None
    latest_image: FBPlantLatestImage | None
    tags: list[FBPlantTag]

    # formatted_botanical_name: str | None  # botanical name in html, populated in root_validator

    # @root_validator(pre=False)
    # def check_card_number_omitted(cls, values):  # noqa
    #     species_name = values.get('botanical_name')
    #     values['formatted_botanical_name'] = values['taxon_authors']
    #     return values

    class Config:
        extra = Extra.forbid
        use_enum_values = True
        orm_mode = True
        allow_population_by_field_name = True


class BPlantsRenameRequest(BaseModel):
    OldPlantName: constr(min_length=1, max_length=100)
    NewPlantName: constr(min_length=1, max_length=100)

    class Config:
        extra = Extra.forbid


class BResultsPlants(BaseModel):
    action: str
    message: BMessage
    PlantsCollection: list[BPlant]

    class Config:
        extra = Extra.forbid


class BResultsPlantsUpdate(BaseModel):
    action: str
    resource: FBMajorResource
    message: BMessage
    plants: list[BPlant]

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class BResultsPlantCloned(BaseModel):
    action: str
    message: BMessage
    plant: BPlant

    class Config:
        extra = Extra.forbid

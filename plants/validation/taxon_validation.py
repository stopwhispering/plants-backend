from pathlib import Path
from typing import List, Optional, Dict
import datetime

from pydantic import validator
from pydantic.fields import Field
from pydantic.main import BaseModel

from plants.validation.message_validation import PMessage
from plants.validation.trait_validation import PTraitCategoryWithTraits
from plants.services.image_services_simple import get_path_for_taxon_thumbnail


class PTaxonInfoRequest(BaseModel):
    includeKew: bool
    searchForGenus: bool
    species: str  # search string

    class Config:
        extra = 'forbid'


class PResultsTaxonInfoRequest(BaseModel):
    action: str
    resource: str
    message: PMessage
    ResultsCollection: List

    class Config:
        extra = 'forbid'


class PAssignTaxonRequest(BaseModel):
    fqId: Optional[str]
    hasCustomName: bool
    id: Optional[int]  # taxon id
    nameInclAddition: str
    plant_id: int
    source: str  # "Local DB" or ...

    class Config:
        extra = 'forbid'


class PFetchTaxonImages(BaseModel):
    gbif_id: int


class PDistribution(BaseModel):
    native: List[str]
    introduced: List[str]

    class Config:
        extra = 'forbid'


class PTaxonImage(BaseModel):
    id: Optional[int]  # empty if initially assigned to taxon
    # path_thumb: Path
    filename: str
    relative_path_thumb: Path = Field(alias='path_thumb')  # todo remove?
    # path_original: Path
    relative_path: Path = Field(alias='path_original')  # todo remove?
    description: Optional[str]

    class Config:
        extra = 'forbid'
        allow_population_by_field_name = True


class PTaxonOccurrenceImage(BaseModel):
    occurrence_id: int
    img_no: int
    gbif_id: int
    scientific_name: str
    basis_of_record: str
    verbatim_locality: Optional[str]
    date: datetime.datetime
    creator_identifier: str
    publisher_dataset: Optional[str]
    references: Optional[str]
    href: str  # link to iamge at inaturalist etc.
    filename_thumbnail: str  # filename for generated thumbnails

    # filename_thumbnail: Path = Field(alias='path_thumbnail')

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True
        # alias_generator = humps.camelize
        allow_population_by_field_name = True  # populate model by both alias (default) and field name

    @validator("date")
    def datetime_to_string(cls, v):  # noqa
        """validator decorator makes this a class method and enforces cls param"""
        # return v.isoformat()
        return v.strftime("%Y-%m-%d")

    # @validator("filename_thumbnail")
    # def get_path(cls, v):  # noqa
    #     """validator decorator makes this a class method and enforces cls param"""
    #     return get_path_for_taxon_thumbnail(v)


class PTaxon(BaseModel):
    id: int
    name: str
    is_custom: bool
    subsp: Optional[str]
    species: Optional[str]  # empty for custom cultivars
    subgen: Optional[str]
    genus: str
    family: str
    phylum: Optional[str]
    kingdom: Optional[str]
    rank: str
    taxonomic_status: Optional[str]
    name_published_in_year: Optional[int]
    synonym: bool
    fq_id: Optional[str]
    authors: Optional[str]
    basionym: Optional[str]
    synonyms_concat: Optional[str]
    distribution_concat: Optional[str]
    hybrid: bool
    hybridgenus: bool
    gbif_id: Optional[str]
    powo_id: Optional[str]
    custom_notes: Optional[str]
    ipni_id_short: str
    distribution: Optional[PDistribution]  # not filled for each request
    images: Optional[List[PTaxonImage]]  # not filled for each request
    trait_categories: Optional[List[PTraitCategoryWithTraits]]  # not filled for each request
    occurrenceImages: Optional[List[PTaxonOccurrenceImage]]

    class Config:
        extra = 'forbid'


class PResultsSaveTaxonRequest(BaseModel):
    action: str
    resource: str
    message: PMessage
    botanical_name: str
    taxon_data: PTaxon

    class Config:
        extra = 'forbid'


class PResultsGetTaxa(BaseModel):
    action: str
    resource: str
    message: Optional[PMessage]
    TaxaDict: Dict[int, PTaxon]

    class Config:
        extra = 'forbid'


class PModifiedTaxa(BaseModel):
    ModifiedTaxaCollection: List[PTaxon]

    class Config:
        extra = 'forbid'


class PResultsFetchTaxonImages(BaseModel):
    action: str
    resource: str
    message: PMessage
    occurrenceImages: Optional[List[PTaxonOccurrenceImage]]

    class Config:
        extra = 'forbid'

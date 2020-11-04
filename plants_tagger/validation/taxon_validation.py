from typing import List, Optional, Dict
import datetime

from pydantic import validator
from pydantic.fields import Field
from pydantic.main import BaseModel
import humps

from plants_tagger.services.image_services import get_path_for_taxon_thumbnail
from plants_tagger.validation.message_validation import PMessage
from plants_tagger.validation.trait_validation import PTraitCategoryWithTraits


class PTaxonId(BaseModel):
    __root__: int


class PTaxonInfoRequest(BaseModel):
    species: str
    includeKew: bool
    searchForGenus: bool

    class Config:
        extra = 'forbid'


class PResultsTaxonInfoRequest(BaseModel):
    action: str
    resource: str
    message: PMessage
    ResultsCollection: List

    class Config:
        extra = 'forbid'


class PSaveTaxonRequest(BaseModel):
    fqId: str
    hasCustomName: bool
    nameInclAddition: str
    source: str
    id: Optional[int]  # taxon id
    plant: str

    class Config:
        extra = 'forbid'


class PDistribution(BaseModel):
    native: List[str]
    introduced: List[str]

    class Config:
        extra = 'forbid'


class PTaxonImage(BaseModel):
    id: Optional[int]  # empty if initially assigned to taxon
    url_small: str
    url_original: str
    description: Optional[str]

    class Config:
        extra = 'forbid'


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
    href: str
    filename_thumbnail: str = Field(alias='path_thumbnail')

    class Config:
        extra = 'forbid'
        anystr_strip_whitespace = True
        alias_generator = humps.camelize
        allow_population_by_field_name = True  # populate model by both alias (default) and field name

    @validator("date")
    def datetime_to_string(cls, v):
        # return v.isoformat()
        return v.strftime("%Y-%m-%d")

    @validator("filename_thumbnail")
    def get_path(cls, v):
        return get_path_for_taxon_thumbnail(v)


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
    message: PMessage
    TaxaDict: Dict[int, PTaxon]

    class Config:
        extra = 'forbid'


class PModifiedTaxa(BaseModel):
    ModifiedTaxaCollection: List[PTaxon]

    class Config:
        extra = 'forbid'

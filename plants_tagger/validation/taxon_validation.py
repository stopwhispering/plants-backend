from typing import List, Optional, Dict

from pydantic.main import BaseModel

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
    id: int
    url_small: str
    url_original: str
    description: Optional[str]

    class Config:
        extra = 'forbid'


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

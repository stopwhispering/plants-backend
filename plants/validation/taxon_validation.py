from enum import Enum
from typing import List, Optional, Dict
import datetime

from pydantic import validator, Extra
from pydantic.main import BaseModel

from plants.validation.message_validation import BMessage


####################################################################################################
# Entities used in <<both>> API Requests from Frontend <<and>> Responses from Backend (FB...)
####################################################################################################
class FBTaxonImage(BaseModel):
    id: Optional[int]  # empty if initially assigned to taxon
    filename: str
    description: Optional[str]

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True


class FBDistribution(BaseModel):
    native: List[str]
    introduced: List[str]

    class Config:
        extra = Extra.forbid


class FBTaxonOccurrenceImage(BaseModel):
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
        extra = Extra.forbid
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


class FBTaxon(BaseModel):
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
    lsid: Optional[str]
    authors: Optional[str]
    basionym: Optional[str]
    synonyms_concat: Optional[str]
    distribution_concat: Optional[str]
    hybrid: bool
    hybridgenus: bool
    gbif_id: Optional[str]
    # powo_id: Optional[str]
    custom_notes: Optional[str]
    # ipni_id_short: str
    distribution: Optional[FBDistribution]  # not filled for each request
    images: Optional[List[FBTaxonImage]]  # not filled for each request
    # trait_categories: Optional[List[PTraitCategoryWithTraits]]  # not filled for each request
    occurrenceImages: Optional[List[FBTaxonOccurrenceImage]]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API <<Requests>> from <<Frontend>> (F...)
####################################################################################################
class FTaxonInfoRequest(BaseModel):
    include_external_apis: bool
    taxon_name_pattern: str
    search_for_genus_not_species: bool

    class Config:
        extra = Extra.forbid


class FModifiedTaxa(BaseModel):
    ModifiedTaxaCollection: List[FBTaxon]

    class Config:
        extra = Extra.forbid


class FFetchTaxonImages(BaseModel):
    gbif_id: int

    class Config:
        extra = Extra.forbid  # todo okay?


class FAssignTaxonRequest(BaseModel):
    lsid: Optional[str]
    hasCustomName: bool
    taxon_id: Optional[int]  # taxon id
    nameInclAddition: str
    plant_id: int
    source: str  # "Local DB" or ...

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API <<Responses>> from <<Backend>> B...)
####################################################################################################
class BSearchResultSource(Enum):
    SOURCE_PLANTS_DB = 'Local DB'
    SOURCE_IPNI = 'Plants of the World'
    SOURCE_IPNI_POWO = 'International Plant Names Index + Plants of the World'


class BKewSearchResultEntry(BaseModel):
    source: BSearchResultSource  # determined upon saving by database
    id: int | None  # determined upon saving by database
    count: int
    count_inactive: int
    is_custom: bool
    synonym: bool | None  # available only in POWO, thus theoretically empty if taxon supplied only by IPNI
    authors: str
    family: str
    name: str
    rank: str
    lsid: str | None  # IPNI Life Sciences Identifier
    # powo_id: str | None
    genus: str
    species: str | None  # None for genus search
    namePublishedInYear: str | None
    phylum: str | None  # available only in POWO, thus theoretically empty if taxon supplied only by IPNI
    synonyms_concat: str | None
    distribution_concat: str | None

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class BResultsTaxonInfoRequest(BaseModel):
    action: str
    # resource: str
    message: BMessage
    ResultsCollection: list[BKewSearchResultEntry]

    class Config:
        extra = Extra.forbid


class BResultsSaveTaxonRequest(BaseModel):
    action: str
    resource: str
    message: BMessage
    botanical_name: str
    taxon_data: FBTaxon

    class Config:
        extra = Extra.forbid


class BResultsFetchTaxonImages(BaseModel):
    action: str
    resource: str
    message: BMessage
    occurrenceImages: Optional[List[FBTaxonOccurrenceImage]]

    class Config:
        extra = Extra.forbid


class BResultsGetTaxa(BaseModel):
    action: str
    resource: str
    message: Optional[BMessage]
    TaxaDict: Dict[int, FBTaxon]

    class Config:
        extra = Extra.forbid

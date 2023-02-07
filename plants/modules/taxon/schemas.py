from enum import Enum
from typing import List, Optional
import datetime

from pydantic import validator, Extra, constr, HttpUrl
from pydantic.main import BaseModel

from plants.modules.image.models import Image
from plants.modules.taxon.models import Distribution
from plants.shared.api_constants import FORMAT_API_YYYY_MM_DD_HH_MM
from plants.shared.message_schemas import BMessage


####################################################################################################
# Entities used in <<both>> API Requests from Frontend <<and>> Responses from Backend (FB...)
####################################################################################################
class FBDistribution(BaseModel):
    native: List[constr(min_length=1, max_length=40)]
    introduced: List[constr(min_length=1, max_length=40)]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API <<Requests>> from <<Frontend>> (F...)
####################################################################################################
class FTaxonOccurrenceImage(BaseModel):
    occurrence_id: int
    img_no: int
    gbif_id: int
    scientific_name: constr(min_length=1, max_length=100)
    basis_of_record: constr(min_length=1, max_length=25)
    verbatim_locality: Optional[constr(min_length=1, max_length=125)]
    date: datetime.datetime
    creator_identifier: constr(min_length=1, max_length=100)
    publisher_dataset: Optional[constr(min_length=1, max_length=100)]
    references: Optional[HttpUrl]
    href: HttpUrl  # link to iamge at inaturalist etc.
    # todo switch to other id
    filename_thumbnail: constr(min_length=1, max_length=120)  # filename for generated thumbnails

    class Config:
        extra = Extra.forbid
        anystr_strip_whitespace = True

    @validator("date")
    def datetime_to_string(cls, v):  # noqa
        """validator decorator makes this a class method and enforces cls param"""
        return v.strftime(FORMAT_API_YYYY_MM_DD_HH_MM)  # todo required for Frontend variant?

    # @validator("filename_thumbnail")
    # def get_path(cls, v):  # noqa
    #     """validator decorator makes this a class method and enforces cls param"""
    #     return get_path_for_taxon_thumbnail(v)


class FTaxonImage(BaseModel):
    id: int
    filename: constr(min_length=1, max_length=150)
    description: Optional[str]

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True


class FTaxon(BaseModel):
    id: int
    name: constr(min_length=1, max_length=100)
    is_custom: bool
    species: Optional[constr(min_length=1, max_length=100)]  # empty for custom cultivars
    genus: constr(min_length=1, max_length=100)
    family: constr(min_length=1, max_length=100)

    infraspecies: constr(min_length=1, max_length=40) | None
    cultivar: constr(min_length=1, max_length=30) | None
    affinis: constr(min_length=1, max_length=40) | None

    rank: constr(min_length=1, max_length=30)
    taxonomic_status: Optional[constr(min_length=1, max_length=100)]
    name_published_in_year: Optional[int]
    synonym: bool
    lsid: Optional[constr(min_length=1, max_length=50)]
    authors: Optional[constr(min_length=1, max_length=100)]
    basionym: Optional[constr(min_length=1, max_length=100)]
    synonyms_concat: Optional[constr(min_length=1, max_length=500)]
    distribution_concat: Optional[constr(min_length=1, max_length=200)]
    hybrid: bool
    hybridgenus: bool
    gbif_id: Optional[int]
    custom_notes: Optional[str]
    distribution: Optional[FBDistribution]  # not filled for each request
    images: Optional[List[FTaxonImage]]  # not filled for each request
    # occurrence_images: Optional[List[FTaxonOccurrenceImage]]  # not sent from frontend (read-only anyway)

    class Config:
        extra = Extra.ignore


class FTaxonInfoRequest(BaseModel):
    include_external_apis: bool
    taxon_name_pattern: str
    search_for_genus_not_species: bool

    class Config:
        extra = Extra.forbid


class FModifiedTaxa(BaseModel):
    ModifiedTaxaCollection: List[FTaxon]

    class Config:
        extra = Extra.forbid


class FBotanicalAttributes(BaseModel):
    rank: str
    genus: str
    species: str | None
    infraspecies: str | None
    hybrid: bool
    hybridgenus: bool
    authors: str | None
    name_published_in_year: int | None

    is_custom: bool
    cultivar: str | None
    affinis: str | None
    custom_rank: str | None
    custom_infraspecies: str | None
    custom_suffix: str | None

    class Config:
        extra = Extra.forbid


class FFetchTaxonOccurrenceImagesRequest(BaseModel):
    gbif_id: int

    class Config:
        extra = Extra.forbid  # todo okay?


class FRetrieveTaxonDetailsRequest(BaseModel):
    lsid: Optional[constr(min_length=1, max_length=50)]
    hasCustomName: bool
    taxon_id: Optional[int]  # taxon id
    nameInclAddition: str
    plant_id: int
    source: str  # "Local DB" or ...  # todo enum

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API <<Responses>> from <<Backend>> B...)
####################################################################################################
class BTaxonOccurrenceImage(BaseModel):
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
        extra = Extra.ignore
        anystr_strip_whitespace = True
        orm_mode = True

    @validator("date")
    def datetime_to_string(cls, v):  # noqa
        """validator decorator makes this a class method and enforces cls param"""
        return v.strftime(FORMAT_API_YYYY_MM_DD_HH_MM)  # todo required for Backend variant?


class BTaxonImage(BaseModel):
    id: int
    filename: str
    description: Optional[str]

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True
        orm_mode = True


class BSearchResultSource(Enum):
    SOURCE_PLANTS_DB = 'Local DB'
    SOURCE_IPNI = 'Plants of the World'
    SOURCE_IPNI_POWO = 'International Plant Names Index + Plants of the World'


class FBRank(str, Enum):
    GENUS = "gen."
    SPECIES = "spec."
    SUBSPECIES = "subsp."
    VARIETY = "var."
    FORMA = "forma"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


def _transform_distribution(distribution: list[Distribution]) -> FBDistribution:
    # distribution codes according to WGSRPD (level 3)
    results = {'native': [], 'introduced': []}
    for dist in distribution:
        if dist.establishment == 'Native':
            results['native'].append(dist.tdwg_code)
        elif dist.establishment == 'Introduced':
            results['introduced'].append(dist.tdwg_code)
    return FBDistribution.parse_obj(results)


class BTaxon(BaseModel):
    id: int
    name: str
    is_custom: bool
    # subsp: Optional[str]
    species: Optional[str]  # empty for custom cultivars

    infraspecies: str | None
    cultivar: str | None
    affinis: str | None

    # subgen: Optional[str]
    genus: str
    family: str
    # phylum: Optional[str]
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
    gbif_id: Optional[int]
    custom_notes: Optional[str]
    distribution: FBDistribution  # not filled for each request
    images: list[BTaxonImage]
    occurrence_images: list[BTaxonOccurrenceImage]

    @validator("images", pre=True)
    def _transform_images(cls, images: list[Image], values, **kwargs) -> list[BTaxonImage]:  # noqa
        """extract major information from Image model; and read the description from
        taxon-to-image link table, not from image itself"""
        results = []
        taxon_id = values['id']
        for image in images:
            image_to_taxon_assignment = next(i for i in image.image_to_taxon_associations if i.taxon_id == taxon_id)
            results.append(BTaxonImage.parse_obj({
                'id': image.id,
                'filename': image.filename,
                'description': image_to_taxon_assignment.description  # !
            }))
        return results

    @validator("distribution", pre=True)
    def _transform_distribution(cls, distribution: list[Distribution]) -> FBDistribution:  # noqa
        # distribution codes according to WGSRPD (level 3)
        results = {'native': [], 'introduced': []}
        for dist in distribution:
            if dist.establishment == 'Native':
                results['native'].append(dist.tdwg_code)
            elif dist.establishment == 'Introduced':
                results['introduced'].append(dist.tdwg_code)
        return FBDistribution.parse_obj(results)

    class Config:
        extra = Extra.forbid
        orm_mode = True


class BKewSearchResultEntry(BaseModel):
    # source: BSearchResultSource  # determined upon saving by database
    id: int | None  # filled only for those already in db
    in_db: bool
    count: int
    count_inactive: int
    synonym: bool
    authors: str
    family: str
    name: str
    rank: str
    taxonomic_status: str
    lsid: str  # IPNI/POWO Life Sciences Identifier
    genus: str
    species: str | None  # None for genus search
    infraspecies: str | None

    is_custom: bool
    custom_rank: FBRank | None
    custom_infraspecies: str | None
    cultivar: str | None
    affinis: str | None
    custom_suffix: str | None

    hybrid: bool
    hybridgenus: bool

    namePublishedInYear: int | None
    basionym: str | None
    # phylum: str
    synonyms_concat: str | None
    distribution_concat: str | None

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class BCreatedTaxonResponse(BaseModel):
    action: str
    message: BMessage
    new_taxon: BTaxon

    class Config:
        extra = Extra.forbid
        orm_mode = True


class FNewTaxon(BaseModel):
    id: int | None  # filled if taxon is already in db

    rank: constr(min_length=1, max_length=30)
    # phylum: str
    family: constr(min_length=1, max_length=100)
    genus: constr(min_length=1, max_length=100)
    species: constr(min_length=1, max_length=100) | None
    infraspecies: constr(min_length=1, max_length=40, strip_whitespace=True) | None

    lsid: constr(min_length=1, max_length=50)  # IPNI/POWO Life Sciences Identifier
    taxonomic_status: constr(min_length=1, max_length=100)
    synonym: bool
    authors: constr(min_length=1, max_length=100)
    namePublishedInYear: int | None
    basionym: constr(min_length=1, max_length=100) | None
    hybrid: bool
    hybridgenus: bool
    synonyms_concat: constr(min_length=1, max_length=500) | None
    distribution_concat: str | None

    is_custom: bool
    custom_rank: FBRank | None
    custom_infraspecies: str | None
    cultivar: str | None
    affinis: str | None
    custom_suffix: str | None

    class Config:
        extra = Extra.forbid
        use_enum_values = True


class BResultsTaxonInfoRequest(BaseModel):
    action: str
    message: BMessage
    ResultsCollection: list[BKewSearchResultEntry]

    class Config:
        extra = Extra.forbid


class BResultsRetrieveTaxonDetailsRequest(BaseModel):
    action: str
    message: BMessage
    botanical_name: str
    taxon_data: BTaxon

    class Config:
        extra = Extra.forbid
        orm_mode = True


class BResultsFetchTaxonImages(BaseModel):
    action: str
    message: BMessage
    occurrence_images: List[BTaxonOccurrenceImage]

    class Config:
        extra = Extra.forbid


class BResultsGetTaxon(BaseModel):
    action: str
    message: BMessage
    taxon: BTaxon

    class Config:
        extra = Extra.forbid
        orm_mode = True


class BResultsGetBotanicalName(BaseModel):
    full_html_name: str
    name: str

    class Config:
        extra = Extra.forbid

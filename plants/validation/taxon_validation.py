from enum import Enum
from typing import List, Optional
import datetime

from pydantic import validator, Extra
from pydantic.main import BaseModel

from plants.models.image_models import Image
from plants.models.taxon_models import Distribution
from plants.util.ui_utils import FORMAT_API_YYYY_MM_DD_HH_MM
from plants.validation.message_validation import BMessage


####################################################################################################
# Entities used in <<both>> API Requests from Frontend <<and>> Responses from Backend (FB...)
####################################################################################################
class FBDistribution(BaseModel):
    native: List[str]
    introduced: List[str]

    class Config:
        extra = Extra.forbid


####################################################################################################
# Entities used only in API <<Requests>> from <<Frontend>> (F...)
####################################################################################################
class FTaxonOccurrenceImage(BaseModel):
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
        # allow_population_by_field_name = True  # populate model by both alias (default) and field name

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
    filename: str
    description: Optional[str]

    class Config:
        extra = Extra.forbid
        allow_population_by_field_name = True


class FTaxon(BaseModel):
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
    custom_notes: Optional[str]
    distribution: Optional[FBDistribution]  # not filled for each request
    images: Optional[List[FTaxonImage]]  # not filled for each request
    occurrence_images: Optional[List[FTaxonOccurrenceImage]]

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


class FFetchTaxonOccurrenceImagesRequest(BaseModel):
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
    lsid: str  # IPNI/POWO Life Sciences Identifier
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

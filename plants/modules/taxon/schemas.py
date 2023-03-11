from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Extra, HttpUrl, constr, validator

from plants.modules.taxon.enums import FBRank
from plants.shared.api_utils import format_api_datetime
from plants.shared.base_schema import BaseSchema, RequestContainer, ResponseContainer

if TYPE_CHECKING:
    from plants.modules.image.models import Image
    from plants.modules.taxon.models import Distribution


class DistributionBase(BaseSchema):
    native: list[constr(min_length=1, max_length=40)]  # type: ignore[valid-type]
    introduced: list[constr(min_length=1, max_length=40)]  # type: ignore[valid-type]


class DistributionRead(DistributionBase):
    pass


class DistributionUpdate(DistributionBase):
    pass


class TaxonOccurrenceImageBase(BaseSchema):
    occurrence_id: int
    img_no: int
    gbif_id: int
    scientific_name: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    basis_of_record: constr(min_length=1, max_length=25)  # type: ignore[valid-type]
    verbatim_locality: Optional[  # type: ignore[valid-type]
        constr(min_length=1, max_length=125)
    ]
    photographed_at: datetime.datetime
    creator_identifier: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    publisher_dataset: Optional[  # type: ignore[valid-type]
        constr(min_length=1, max_length=100)
    ]
    references: Optional[HttpUrl]
    href: HttpUrl  # link to iamge at inaturalist etc.

    filename_thumbnail: constr(  # type: ignore[valid-type]
        min_length=1, max_length=120
    )  # filename for generated thumbnails


class TaxonOccurrenceImageRead(TaxonOccurrenceImageBase):
    class Config:
        extra = Extra.ignore

    # noinspection PyMethodParameters
    # @validator("created_on")
    @validator("photographed_at")
    def datetime_to_string(cls, v: datetime.datetime) -> str:
        """Validator decorator makes this a class method and enforces cls param."""
        return format_api_datetime(v)


class TaxonImageBase(BaseSchema):
    id: int
    description: Optional[str]


class TaxonImageUpdate(TaxonImageBase):
    class Config:
        allow_population_by_field_name = True


class TaxonImageRead(TaxonImageBase):
    pass


class FTaxonInfoRequest(RequestContainer):
    include_external_apis: bool
    taxon_name_pattern: str
    search_for_genus_not_species: bool


class FBotanicalAttributes(BaseSchema):
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
    custom_rank: FBRank | None
    custom_infraspecies: str | None
    custom_suffix: str | None


class FFetchTaxonOccurrenceImagesRequest(RequestContainer):
    gbif_id: int


class BKewSearchResultEntry(BaseSchema):
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

    name_published_in_year: int | None
    basionym: str | None
    # phylum: str
    synonyms_concat: str | None
    distribution_concat: str | None


class TaxonBase(BaseSchema):
    rank: constr(min_length=1, max_length=30)  # type: ignore[valid-type]
    family: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    genus: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    species: constr(min_length=1, max_length=100) | None  # type: ignore[valid-type]
    infraspecies: constr(min_length=1, max_length=40) | None  # type: ignore[valid-type]

    # IPNI/POWO Life Sciences Identifier
    lsid: constr(min_length=1, max_length=50)  # type: ignore[valid-type]
    taxonomic_status: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    synonym: bool
    authors: constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    name_published_in_year: int
    basionym: constr(min_length=1, max_length=100) | None  # type: ignore[valid-type]
    hybrid: bool
    hybridgenus: bool
    synonyms_concat: constr(  # type: ignore[valid-type]
        min_length=1, max_length=500
    ) | None
    distribution_concat: str | None

    is_custom: bool
    cultivar: str | None
    affinis: str | None


# class TaxonUpdate(TaxonBase):
class TaxonUpdate(BaseSchema):
    id: int
    # name: constr(min_length=1, max_length=100)

    # gbif_id: Optional[int]
    custom_notes: Optional[str]
    # distribution: Optional[DistributionUpdate]  # not filled for each request
    images: Optional[list[TaxonImageUpdate]]  # not filled for each request

    class Config:
        extra = Extra.ignore


class TaxonRead(TaxonBase):
    id: int
    name: str
    gbif_id: Optional[int]
    custom_notes: Optional[str]
    distribution: DistributionRead  # not filled for each request
    images: list[TaxonImageRead]
    occurrence_images: list[TaxonOccurrenceImageRead]

    # noinspection PyMethodParameters
    @validator("images", pre=True)
    def _transform_images(
        cls, images: list[Image], values: dict[str, Any]
    ) -> list[TaxonImageRead]:
        """Extract major information from Image model; and read the description from
        taxon-to-image link table, not from image itself."""
        results = []
        taxon_id = values["id"]
        for image in images:
            image_to_taxon_assignment = next(
                i for i in image.image_to_taxon_associations if i.taxon_id == taxon_id
            )
            results.append(
                TaxonImageRead.parse_obj(
                    {
                        "id": image.id,
                        "description": image_to_taxon_assignment.description,  # !
                    }
                )
            )
        return results

    # noinspection PyMethodParameters
    @validator("distribution", pre=True)
    def _transform_distribution(
        cls, distribution: list[Distribution]
    ) -> DistributionRead:
        # distribution codes according to WGSRPD (level 3)
        results: dict[str, list[str]] = {"native": [], "introduced": []}
        for dist in distribution:
            if dist.establishment == "Native":
                results["native"].append(dist.tdwg_code)
            elif dist.establishment == "Introduced":
                results["introduced"].append(dist.tdwg_code)
        return DistributionRead.parse_obj(results)

    class Config:
        extra = Extra.forbid
        orm_mode = True


class TaxonCreate(TaxonBase):
    id: int | None  # filled if taxon is already in db
    custom_rank: FBRank | None
    custom_infraspecies: str | None
    custom_suffix: str | None


class BResultsTaxonInfoRequest(ResponseContainer):
    ResultsCollection: list[BKewSearchResultEntry]


class BResultsRetrieveTaxonDetailsRequest(ResponseContainer):
    botanical_name: str
    taxon_data: TaxonRead


class BResultsFetchTaxonImages(ResponseContainer):
    occurrence_images: list[TaxonOccurrenceImageRead]


class BResultsGetTaxon(ResponseContainer):
    taxon: TaxonRead


class BResultsGetBotanicalName(BaseSchema):
    full_html_name: str
    name: str


class BCreatedTaxonResponse(ResponseContainer):
    new_taxon: TaxonRead


class FModifiedTaxa(RequestContainer):
    ModifiedTaxaCollection: list[TaxonUpdate]

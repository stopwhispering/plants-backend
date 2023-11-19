from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, field_validator, model_validator, networks, types

from plants.modules.taxon.enums import Establishment, FBRank
from plants.shared.api_utils import format_api_datetime
from plants.shared.base_schema import BaseSchema, RequestContainer, ResponseContainer

if TYPE_CHECKING:
    from plants.modules.image.models import Image
    from plants.modules.taxon.models import Distribution


class DistributionBase(BaseSchema):
    native: list[types.constr(min_length=1, max_length=40)]  # type: ignore[valid-type]
    introduced: list[types.constr(min_length=1, max_length=40)]  # type: ignore[valid-type]


class DistributionRead(DistributionBase):
    pass


class DistributionUpdate(DistributionBase):
    pass


class TaxonOccurrenceImageBase(BaseSchema):
    occurrence_id: int
    img_no: int
    gbif_id: int
    scientific_name: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    basis_of_record: types.constr(min_length=1, max_length=25)  # type: ignore[valid-type]
    verbatim_locality: types.constr(min_length=1, max_length=125) | None = None  # type: ignore[valid-type]
    photographed_at: datetime.datetime
    creator_identifier: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    publisher_dataset: types.constr(min_length=1, max_length=100) | None = None  # type: ignore[valid-type]

    references: networks.HttpUrl | None = None
    href: networks.HttpUrl  # link to iamge at inaturalist etc.


class TaxonOccurrenceImageRead(TaxonOccurrenceImageBase):
    model_config = ConfigDict(extra="ignore")

    # noinspection PyMethodParameters
    # @validator("created_on")
    @field_validator("photographed_at")
    @classmethod
    def datetime_to_string(cls, dt: datetime.datetime) -> str:
        """Validator decorator makes this a class method and enforces cls param."""
        return format_api_datetime(dt)


class TaxonImageBase(BaseSchema):
    id: int
    description: str | None = None


class TaxonImageUpdate(TaxonImageBase):
    model_config = ConfigDict(populate_by_name=True)


class TaxonImageRead(TaxonImageBase):
    pass


class FTaxonInfoRequest(RequestContainer):
    include_external_apis: bool
    taxon_name_pattern: str
    search_for_genus_not_species: bool


class FBotanicalAttributes(BaseSchema):
    rank: str
    genus: str
    species: str | None = None
    infraspecies: str | None = None
    hybrid: bool
    hybridgenus: bool
    authors: str | None = None
    name_published_in_year: int | None = None

    is_custom: bool
    cultivar: str | None = None
    affinis: str | None = None
    custom_rank: FBRank | None = None
    custom_infraspecies: str | None = None
    custom_suffix: str | None = None


class FFetchTaxonOccurrenceImagesRequest(RequestContainer):
    gbif_id: int


class BKewSearchResultEntry(BaseSchema):
    # source: BSearchResultSource  # determined upon saving by database
    id: int | None = None  # filled only for those already in db
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
    species: str | None = None  # None for genus search
    infraspecies: str | None = None

    is_custom: bool
    custom_rank: FBRank | None = None
    custom_infraspecies: str | None = None
    cultivar: str | None = None
    affinis: str | None = None
    custom_suffix: str | None = None

    hybrid: bool
    hybridgenus: bool

    name_published_in_year: int | None = None  # rarely None
    basionym: str | None = None
    # phylum: str
    synonyms_concat: str | None = None
    distribution_concat: str | None = None


class TaxonBase(BaseSchema):
    rank: types.constr(min_length=1, max_length=30)  # type: ignore[valid-type]
    family: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    genus: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    species: types.constr(min_length=1, max_length=100) | None = None  # type: ignore[valid-type]
    infraspecies: types.constr(min_length=1, max_length=40) | None = None  # type: ignore[valid-type]

    # IPNI/POWO Life Sciences Identifier
    lsid: types.constr(min_length=1, max_length=50)  # type: ignore[valid-type]
    taxonomic_status: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    synonym: bool
    authors: types.constr(min_length=1, max_length=100)  # type: ignore[valid-type]
    name_published_in_year: int | None = None  # rarely None
    basionym: types.constr(min_length=1, max_length=100) | None = None  # type: ignore[valid-type]
    hybrid: bool
    hybridgenus: bool
    synonyms_concat: types.constr(min_length=1, max_length=500) | None = None  # type: ignore[valid-type]
    distribution_concat: str | None = None

    is_custom: bool
    cultivar: str | None = None
    affinis: str | None = None


# class TaxonUpdate(TaxonBase):
class TaxonUpdate(BaseSchema):
    id: int
    # name: types.constr(min_length=1, max_length=100)

    # gbif_id: Optional[int]
    custom_notes: str | None = None
    # distribution: Optional[DistributionUpdate]  # not filled for each request
    images: list[TaxonImageUpdate] | None = None  # not filled for each request

    model_config = ConfigDict(extra="ignore")


class TaxonRead(TaxonBase):
    id: int
    name: str
    gbif_id: int | None = None
    custom_notes: str | None = None
    distribution: DistributionRead  # not filled for each request
    images: list[TaxonImageRead]
    occurrence_images: list[TaxonOccurrenceImageRead]

    # noinspection PyMethodParameters
    @field_validator("images", mode="before")
    @classmethod
    def _transform_images(cls, images: list[Image], values: dict[str, Any]) -> list[TaxonImageRead]:
        """Extract major information from Image model; and read the description from taxon-to-image
        link table, not from image itself."""
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
    @field_validator("distribution", mode="before")
    @classmethod
    def _transform_distribution(cls, distribution: list[Distribution]) -> DistributionRead:
        # distribution codes according to WGSRPD (level 3)
        results: dict[str, list[str]] = {"native": [], "introduced": []}
        for dist in distribution:
            if dist.establishment == Establishment.NATIVE:
                results["native"].append(dist.tdwg_code)
            elif dist.establishment == Establishment.INTRODUCED:
                results["introduced"].append(dist.tdwg_code)
        return DistributionRead.parse_obj(results)

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class TaxonCreate(TaxonBase):
    id: int | None  # filled if taxon is already in db
    custom_rank: FBRank | None
    custom_infraspecies: str | None = None
    custom_suffix: str | None = None

    @model_validator(mode="before")
    @classmethod
    def len_truncator(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Truncate to max length in db."""
        if values["distribution_concat"] is not None and len(values["distribution_concat"]) > 200:
            values["distribution_concat"] = values["distribution_concat"][:197] + "..."
        return values


class ResultsTaxonInfoRequest(ResponseContainer):
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

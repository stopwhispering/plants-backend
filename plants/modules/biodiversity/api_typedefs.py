from __future__ import annotations

from typing import NotRequired, TypedDict


class GbifMediaDict(TypedDict):
    format: NotRequired[str]
    created: NotRequired[str]  # '2022-06-21T13:05:00'
    identifiedBy: NotRequired[str]
    creator: NotRequired[str]
    publisher: NotRequired[str]
    references: NotRequired[str]
    identifier: NotRequired[str]


class GbifOccurrenceResultDict(TypedDict):
    basisOfRecord: str
    countryCode: NotRequired[str]
    key: int
    eventDate: NotRequired[str]  # '2022-06-21T13:05:00'
    scientificName: str
    verbatimLocality: NotRequired[str]
    locality: NotRequired[str]
    stateProvince: NotRequired[str]
    identifiedBy: NotRequired[str]
    recordedBy: NotRequired[str]
    publisher: NotRequired[str]
    institutionCode: NotRequired[str]
    rightsHolder: NotRequired[str]
    datasetName: NotRequired[str]
    collectionCode: NotRequired[str]
    references: NotRequired[str]

    media: list[GbifMediaDict]


class GbifOccurrenceResultResponse(TypedDict):
    results: list[GbifOccurrenceResultDict]


class IpniSearchResultTaxonDict(TypedDict):
    inPowo: bool
    fqId: str  # == lsid
    publicationYear: int
    name: str
    family: str
    genus: str
    species: str
    infraspecies: str
    hybrid: bool
    hybridGenus: bool
    rank: str

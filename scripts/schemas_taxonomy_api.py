from typing import List, Optional
from pydantic import BaseModel, Field, AnyUrl
from uuid import UUID
from datetime import datetime


# https://techdocs.gbif.org/en/openapi/v1/species#/Species/getNameUsageChildren
class GbifNameUsage(BaseModel):
    key: int
    nubKey: Optional[int]
    nameKey: Optional[int]
    taxonID: Optional[str]
    sourceTaxonKey: Optional[int] = None
    kingdom: Optional[str]
    phylum: Optional[str]
    order: Optional[str]
    family: Optional[str]
    genus: Optional[str]
    subgenus: Optional[str] = None
    species: Optional[str]
    kingdomKey: Optional[int]
    phylumKey: Optional[int]
    classKey: Optional[int]
    orderKey: Optional[int]
    familyKey: Optional[int]
    genusKey: Optional[int]
    subgenusKey: Optional[int] = None
    speciesKey: Optional[int]
    datasetKey: UUID
    constituentKey: Optional[UUID]
    parentKey: Optional[int]
    parent: Optional[str]
    proParteKey: Optional[int] = None
    acceptedKey: Optional[int] = None
    accepted: Optional[str] = None
    basionymKey: Optional[int] = None
    basionym: Optional[str] = None
    scientificName: str
    canonicalName: Optional[str] = None
    vernacularName: Optional[str] = None
    authorship: Optional[str]
    nameType: Optional[str]
    rank: Optional[str]
    origin: str
    taxonomicStatus: Optional[str]
    nomenclaturalStatus: Optional[List[str]]
    remarks: Optional[str]
    publishedIn: Optional[str] = None
    accordingTo: Optional[str] = None
    numDescendants: Optional[int]
    references: Optional[AnyUrl] = None
    modified: Optional[datetime] = None
    deleted: Optional[datetime] = None
    lastCrawled: Optional[datetime]
    lastInterpreted: Optional[datetime]
    issues: List[str] = Field(default_factory=list)
    class_: Optional[str] = Field(None, alias="class")  # "class" is a reserved keyword


class GbifPagingResponseNameUsage(BaseModel):
    offset: int = Field(ge=0)
    limit: int = Field(ge=0)
    endOfRecords: bool
    count: Optional[int] = None
    results: List[GbifNameUsage]


class SpeciesEssentials(BaseModel):
    nubKey: int
    family: str
    genus: str
    species: str
    basionym: Optional[str] = None
    scientificName: str
    # canonicalName: str  # "Haworthia truncata maughanii" is not very helpful
    publishedIn: Optional[str] = None
    rank: str

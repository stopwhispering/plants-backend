import aiohttp
import logging
import asyncio
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from plants import local_config
from plants.modules.plant.models import Plant
from plants.modules.plant.plant_dal import PlantDAL
from plants.modules.plant.services import fetch_plants
import csv
from pydantic import BaseModel, Field, AnyUrl
from uuid import UUID
from datetime import datetime
from typing import Any

from scripts.schemas_taxonomy_api import GbifPagingResponseNameUsage, GbifNameUsage, \
    SpeciesEssentials

logger = logging.getLogger(__name__)
SPECIES_NUBKEY_HAWORTHIA = 2779529

REST_API_URL_GBIF_CHILDREN = "https://api.gbif.org/v1/species/{nubKey}/children?rank=SPECIES&limit=1000"

IGNORED_NUB_KEYS: List[int] = [
    4931239,  # Haworthia chlorocantha Haw. (-> typo)
    7326851,  # Haworthia pygmaea f. pygmaea (-> can't handle both a forma and a variety)

]


async def _get_gbif_children(nub_key: int) -> List[GbifNameUsage]:
    url = REST_API_URL_GBIF_CHILDREN.format(nubKey=nub_key)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise ValueError(
                    f"Error at GET request for GBIF REST API: {response.status}"
                )
            response_species: dict = await response.json()  # noqa
            response: GbifPagingResponseNameUsage = GbifPagingResponseNameUsage.model_validate(response_species)
    children = response.results

    # discarding if not accepted
    # count species with axonomicStatus != ACCEPTED
    bad_taxonomic_status = set(
        s.taxonomicStatus for s in children if s.taxonomicStatus != "ACCEPTED"
    )
    for status in bad_taxonomic_status:
        n = len([s for s in children if s.taxonomicStatus == status])
        logger.warning(
            f"Discarding {n} entities with taxonomicStatus {status}."
        )

    children = [s for s in children if s.taxonomicStatus == "ACCEPTED"]

    # discarded entities (e.g. typos)
    children = [
        s for s in children if s.nubKey not in IGNORED_NUB_KEYS
    ]

    return children


def _trim_properties(taxa: List[GbifNameUsage]) -> List[SpeciesEssentials]:
    """replace species with species only (e.g. "Haworthia chlorocantha" -> "chlorocantha")
     and other transformations; extract essential fields."""

    essential_fields = SpeciesEssentials.model_fields.keys()
    species_essentials: List[SpeciesEssentials] = []

    for t in taxa:
        if t.rank == "SPECIES":
            # assert t.genus and t.species and not t.variety and not t.form
            species = t.species.replace(f"{t.genus} ", "")
            variety = None
            form = None
        elif t.rank == "VARIETY":
            # assert t.genus and t.species and t.variety and not t.form
            # e.g. "Haworthia chloracantha var. subglauca" -> "chloracantha subglauca"
            species = t.species.replace(f"{t.genus} ", "")
            variety = (t.canonicalName.replace(f"{t.genus} ", "")
                                    .replace(f"{species} ", ""))
            form = None
        elif t.rank == "FORM":
            # assert t.genus and t.species and t.variety and not t.form
            # e.g. "Haworthia chloracantha var. subglauca" -> "chloracantha subglauca"
            species = t.species.replace(f"{t.genus} ", "")
            variety = None
            form = (t.canonicalName.replace(f"{t.genus} ", "")
                                    .replace(f"{species} ", ""))
        else:
            raise ValueError(
                f"Unexpected rank {t.rank} for {t.scientificName}. "
                f"Expected one of: SPECIES, VARIETY, FORM."
            )

        sp_dict = {k: v for k, v in t.model_dump().items() if k in essential_fields}
        sp_dict["species"] = species
        sp_dict["variety"] = variety
        sp_dict["form"] = form
        sp = SpeciesEssentials.model_validate(sp_dict)
        species_essentials.append(sp)

    return species_essentials


async def get_gbif_species(genus_nub_key: int) -> List[SpeciesEssentials]:
    species = await _get_gbif_children(nub_key=genus_nub_key)

    # next we request the varieties for each species (it seems there is no automatic way)
    species_with_varieties: List[GbifNameUsage] = []
    for sp in species:
        species_with_varieties.append(sp)
        if sp.numDescendants == 0:
            continue

        # get varieties for this species
        varieties = await _get_gbif_children(nub_key=sp.key)
        if not len(varieties) >= 2:
            raise ValueError(
                f"Expected at least 2 varieties for {sp.scientificName}, but got {len(varieties)}."
            )

        if varieties:

            # some varieties are bullshit taxa (e.g. "SH1218452.09FU")
            discard_varieties = [
                v for v in varieties if v.rank == 'UNRANKED'
            ]
            if discard_varieties:
                discard_varieties_names = [v.scientificName for v in discard_varieties]
                logger.warning(
                    f"Discarded {len(discard_varieties)} varieties with rank UNRANKED for "
                    f"{sp.scientificName}. Names: {', '.join(discard_varieties_names)}."
                )
                varieties = [v for v in varieties if v not in discard_varieties]

            # the species itself is included in the children, but in a truncated form; we need
            # to identify and discard it; for some unknown reason, the authorship is missing
            # for this base variety
            base_candidates = [v for v in varieties if not v.authorship]
            if len(base_candidates) != 1:
                raise ValueError(
                    f"Expected exactly one base variety for {sp.scientificName}, but got {len(base_candidates)}."
                )
            varieties = [
                v for v in varieties if v.key != base_candidates[0].key
            ]

            # add all varieties
            species_with_varieties.extend(varieties)

    species_with_varieties_essential = _trim_properties(species_with_varieties)

    return species_with_varieties_essential


def assign_plants_to_species(
    species: List[SpeciesEssentials], plants: List[SpeciesEssentials]
) -> List[SpeciesEssentials]:
    """Species includes varieties"""
    for sp in species:
        # sp.plants = [p for p in plants if p.scientificName == sp.scientificName]
        assigned_plants = []
        same_species_plants = [
            p for p in plants if p.taxon and p.taxon.genus == sp.genus and p.taxon.species == sp.species
        ]
        for p in same_species_plants:
            if p.taxon.rank == 'spec.' and sp.rank != 'SPECIES':
                continue
            if p.taxon.rank == 'var.' and sp.rank != 'VARIETY':
                continue
            if p.taxon.rank == 'form.' and sp.rank != 'FORM':
                continue
            if sp.rank == 'FORM':
                a = 1
            if p.taxon.rank == 'form.':
                a = 1

            if p.taxon.rank == 'spec.':
                assert not p.taxon.infraspecies
                assert not sp.variety
                assert not sp.form
                a = 1

            elif p.taxon.rank == 'var.':
                assert p.taxon.infraspecies
                assert sp.variety
                assert not sp.form
                if p.taxon.infraspecies != sp.variety:
                    continue
                a = 1

            elif p.taxon.rank == 'form.':
                assert p.taxon.infraspecies
                assert not sp.variety
                assert sp.form
                if p.taxon.infraspecies != sp.form:
                    continue
                a = 1

            else:
                raise ValueError("Unexpected rank: "
                                 f"{p.taxon.rank} for {p.taxon.scientificName}.")
            assigned_plants.append(p)
        if assigned_plants:
            sp.plant_names = ", ".join(
                [f'{p.id} {p.plant_name}' for p in assigned_plants]
            )

    return species


async def read_plants_from_db() -> List[Plant]:
    # instantiate a db session
    engine = create_async_engine(local_config.connection_string)
    # session: AsyncSession = AsyncSession(engine)
    async with AsyncSession(engine) as session:
        plant_dal = PlantDAL(session=session)
        plants = await fetch_plants(plant_dal=plant_dal)
    plants = [p for p in plants if not p.deleted]
    plants = [p for p in plants if p.active]
    return plants


plants = asyncio.run(read_plants_from_db())
species_with_varieties = asyncio.run(get_gbif_species(SPECIES_NUBKEY_HAWORTHIA))
species_with_varieties = assign_plants_to_species(
    species=species_with_varieties, plants=plants
)

# write response to a csv file; include all fields
with open("gbif_species4.csv", "w", newline="", encoding="utf-8") as csvfile:
    # fieldnames = GbifNameUsage.model_fields.keys()
    fieldnames = SpeciesEssentials.model_fields.keys()
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for result in species_with_varieties:
        writer.writerow(result.model_dump())

# asyncio.run(get_gbif_species(8097702))






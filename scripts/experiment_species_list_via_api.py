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
import pandas as pd
from pydantic import BaseModel, Field, AnyUrl
from uuid import UUID
from datetime import datetime
from typing import Any

from scripts.schemas_taxonomy_api import GbifPagingResponseNameUsage, GbifNameUsage, \
    SpeciesEssentials

logger = logging.getLogger(__name__)
SPECIES_NUBKEY_HAWORTHIA = 2779529
SPECIES_NUBKEY_HAWORTHIOPSIS = 9233780
SPECIES_NUBKEY_GASTERIA = 2778529
SPECIES_NUBKEY_TULISTA = 2777074
SPECIES_NUBKEY_ASTROLOBA = 8386858

REST_API_URL_GBIF_CHILDREN = "https://api.gbif.org/v1/species/{nubKey}/children?rank=SPECIES&limit=1000"

IGNORED_NUB_KEYS: List[int] = [
    4931239,  # Haworthia chlorocantha Haw. (-> typo)
    7326851,  # Haworthia pygmaea f. pygmaea (-> can't handle both a forma and a variety)
    9394434,  # Haworthiopsis reinwardtii f. reinwardtii

]
MANUAL_MAPPING_PLANT_BOTANICAL_NAME_NAME_TO_GBIF_NUB_KEY: dict[str, int] = {
    "Haworthia aff. cooperi var. leightonii": 2780121,
    "Tulista aff. pumila": 9366225,
}


async def _get_gbif_children(nub_key: int) -> List[GbifNameUsage]:
    url = REST_API_URL_GBIF_CHILDREN.format(nubKey=nub_key)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise ValueError(
                    f"Error at GET request for GBIF REST API: {response.status}"
                )
            response_species: dict = await response.json()  # noqa
            response: GbifPagingResponseNameUsage = GbifPagingResponseNameUsage.model_validate(
                response_species)
    children = response.results

    # for whatever reason, gbif returns an unranked tulista genus as tulista child
    children = [c for c in children if c.rank != "UNRANKED"]

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
            subspecies = None
            variety = None
            form = None
        elif t.rank == "VARIETY":
            # assert t.genus and t.species and t.variety and not t.form
            # e.g. "Haworthia chloracantha var. subglauca" -> "chloracantha subglauca"
            species = t.species.replace(f"{t.genus} ", "")
            subspecies = None
            variety = (t.canonicalName.replace(f"{t.genus} ", "")
                       .replace(f"{species} ", ""))
            form = None
        elif t.rank == "FORM":
            # assert t.genus and t.species and t.variety and not t.form
            # e.g. "Haworthia chloracantha var. subglauca" -> "chloracantha subglauca"
            species = t.species.replace(f"{t.genus} ", "")
            subspecies = None
            variety = None
            form = (t.canonicalName.replace(f"{t.genus} ", "")
                    .replace(f"{species} ", ""))
        elif t.rank == "SUBSPECIES":
            # assert t.genus and t.species and t.variety and not t.form
            # e.g. "Haworthia chloracantha var. subglauca" -> "chloracantha subglauca"
            species = t.species.replace(f"{t.genus} ", "")
            subspecies = (t.canonicalName.replace(f"{t.genus} ", "")
                          .replace(f"{species} ", ""))
            variety = None
            form = None
        else:
            raise ValueError(
                f"Unexpected rank {t.rank} for {t.scientificName}. "
                f"Expected one of: SPECIES, VARIETY, FORM, SUBSPECIES."
            )

        sp_dict = {k: v for k, v in t.model_dump().items() if k in essential_fields}
        sp_dict["species"] = species
        sp_dict["subspecies"] = subspecies
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
            # in rare cases, we have multiple varieties, but all of them DOUBTFUL (except type variety)
            if sp.key in [
                2778642,  # Gasteria acinacifolia (J.Jacq.) Haw. has only doubtful variety
                2778765,  # Gasteria glauca van Jaarsv. has only some bullshit SH... variety
                2778270,  # Astroloba rubriflora (L.Bolus) Gideon F.Sm. & J.C.Manning has
                          # only one bullshit SH... variety and a DOUBTFUL variety
            ]:
                varieties = []
            else:
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
) -> tuple[List[SpeciesEssentials], List[str]]:
    """Species includes varieties"""
    assigned_plants_all = []
    for sp in species:
        # sp.plants = [p for p in plants if p.scientificName == sp.scientificName]
        assigned_plants = []
        KEY_SAME_TAXON_MAPPING = {
            "bicolor": "obliqua",
            # Gasteria bicolor Haw. -> Gasteria obliqua (Aiton) Duval (acc. by GBIF)
        }
        same_species_plants = [
            p for p in plants
            if p.taxon
               and p.taxon.genus == sp.genus
               and (p.taxon.species == sp.species
                    or KEY_SAME_TAXON_MAPPING.get(p.taxon.species, None) == sp.species
                    )
        ]
        for p in same_species_plants:
            if p.taxon.rank == 'spec.' and sp.rank != 'SPECIES':
                continue
            if p.taxon.rank == 'var.' and sp.rank != 'VARIETY':
                continue
            if p.taxon.rank == 'forma' and sp.rank != 'FORM':
                continue

            if p.taxon.rank == 'spec.':
                assert not p.taxon.infraspecies
                assert not sp.subspecies
                assert not sp.variety
                assert not sp.form

            elif p.taxon.rank == 'var.':
                assert p.taxon.infraspecies
                assert not sp.subspecies
                assert sp.variety
                assert not sp.form
                if p.taxon.infraspecies != sp.variety:
                    continue

            elif p.taxon.rank == 'forma':
                assert p.taxon.infraspecies
                assert not sp.subspecies
                assert not sp.variety
                assert sp.form
                if p.taxon.infraspecies != sp.form:
                    continue

            elif p.taxon.rank == 'subsp.':
                assert p.taxon.infraspecies
                assert sp.subspecies
                assert not sp.variety
                assert not sp.form
                if p.taxon.infraspecies != sp.subspecies:
                    continue

            else:
                raise ValueError("Unexpected rank: "
                                 f"{p.taxon.rank} for {p.taxon.name}.")
            assigned_plants.append(p)

        # MANUAL_MAPPING_TAXON_NAME_TO_GBIF_NUB_KEY has mappings from plant.name to a gbif nub key
        # background: e.g. affinis plants not correctly assigned otherwise
        manually_mapped_plants = [
            p for p in plants if
            MANUAL_MAPPING_PLANT_BOTANICAL_NAME_NAME_TO_GBIF_NUB_KEY.get(p.botanical_name,
                                                                         None) == sp.key
        ]
        assigned_plants.extend(manually_mapped_plants)

        if assigned_plants:

            # check if any is already assigned, i.e. in assigned_plants_all
            already_assigned_plants = [
                p for p in assigned_plants if p in assigned_plants_all
            ]
            if already_assigned_plants:
                raise ValueError(
                    f"Plants {', '.join([p.botanical_name for p in already_assigned_plants])} "
                    f"already assigned to species {sp.scientificName}."
                )

            sp.plant_names = "\n".join(
                [f'{p.id} {p.plant_name}' for p in assigned_plants]
            )
            assigned_plants_all.extend(assigned_plants)

    plants_not_assigned = [
        p for p in plants if p not in assigned_plants_all
    ]
    # sort by plant_name
    plants_not_assigned = sorted(plants_not_assigned, key=lambda p: p.plant_name)
    plants_not_assigned = [f'{p.id} {p.plant_name}' for p in plants_not_assigned]

    return species, plants_not_assigned


async def read_plants_from_db() -> List[Plant]:
    # instantiate a db session
    engine = create_async_engine(local_config.connection_string)
    # session: AsyncSession = AsyncSession(engine)
    async with AsyncSession(engine) as session:
        plant_dal = PlantDAL(session=session)
        plants = await fetch_plants(plant_dal=plant_dal)
    plants = [p for p in plants if not p.deleted]
    plants = [p for p in plants if p.active]

    BOTANICAL_NAME_PATTERNS = [
        'aworth',  # Haworthia, Haworthiopsis
        'aster',  # Gasteria
        'stro',  # Astroloba
        'list',  # Tulista
    ]
    plants = [
        p for p in plants if any(
            pattern in p.plant_name for pattern in BOTANICAL_NAME_PATTERNS
        )
    ]
    return plants


plants = asyncio.run(read_plants_from_db())
tulist_with_varieties = asyncio.run(get_gbif_species(SPECIES_NUBKEY_TULISTA))
astroloba_with_varieties = asyncio.run(get_gbif_species(SPECIES_NUBKEY_ASTROLOBA))
gasteria_with_varieties = asyncio.run(get_gbif_species(SPECIES_NUBKEY_GASTERIA))
haworthia_with_varieties = asyncio.run(get_gbif_species(SPECIES_NUBKEY_HAWORTHIA))
haworthiopsis_with_varieties = asyncio.run(get_gbif_species(SPECIES_NUBKEY_HAWORTHIOPSIS))
species_with_varieties = (
        haworthia_with_varieties
        + haworthiopsis_with_varieties
        + gasteria_with_varieties
        + tulist_with_varieties
        + astroloba_with_varieties
)
# asyncio.run(get_gbif_species(8097702))
species_with_varieties, plants_not_assigned = assign_plants_to_species(
    species=species_with_varieties, plants=plants
)

# # write response to a csv file; include all fields
# with open("gbif_species4.csv", "w", newline="", encoding="utf-8") as csvfile:
#     # fieldnames = GbifNameUsage.model_fields.keys()
#     fieldnames = SpeciesEssentials.model_fields.keys()
#     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#     writer.writeheader()
#     for result in species_with_varieties:
#         writer.writerow(result.model_dump())

# and xlsx
df = pd.DataFrame([s.model_dump() for s in species_with_varieties])

# add plants_not_assigned, just in the last column as new rows
if plants_not_assigned:
    df_plants_not_assigned = pd.DataFrame(
        {"plant_names": plants_not_assigned}
    )
    df = pd.concat([df, df_plants_not_assigned], ignore_index=True)

df.to_excel("gbif_species.xlsx", index=False, engine='openpyxl')

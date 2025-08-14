import aiohttp
import logging
import asyncio
from typing import List, Optional
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


async def get_gbif_species(genus_nub_key: int) -> int | None:
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

    # boil down to essential fields (SpeciesEssentials schema)
    essential_fields = SpeciesEssentials.model_fields.keys()
    species_with_varieties: List[SpeciesEssentials] = [
        SpeciesEssentials.model_validate({k: v for k, v in s.model_dump().items() if k in essential_fields})
        for s in species_with_varieties
    ]
    a = 1

    # print(response.results)

    # write response to a csv file; include all fields
    import csv
    with open("gbif_species3.csv", "w", newline="", encoding="utf-8") as csvfile:
        # fieldnames = GbifNameUsage.model_fields.keys()
        fieldnames = SpeciesEssentials.model_fields.keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in species_with_varieties:
            writer.writerow(result.model_dump())




    a = 1


# test it
asyncio.run(get_gbif_species(SPECIES_NUBKEY_HAWORTHIA))
# asyncio.run(get_gbif_species(8097702))



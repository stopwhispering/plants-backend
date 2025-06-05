from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from plants.modules.taxon.enums import FBRank

if TYPE_CHECKING:
    from httpx import AsyncClient

    from plants.modules.taxon.models import Taxon


@pytest.mark.asyncio()
async def test_search_taxon(
    ac: AsyncClient,
) -> None:
    payload = {  # FTaxonInfoRequest
        "include_external_apis": True,
        "taxon_name_pattern": "Haworthiopsis koelmaniorum",
        "search_for_genus_not_species": False,
    }
    response = await ac.post("/api/search_taxa_by_name", json=payload)
    assert response.status_code == 200
    results = response.json()["ResultsCollection"]
    assert len(results) == 2

    result = next(r for r in results if r["name"] == "Haworthiopsis koelmaniorum var. mcmurtryi")
    assert result["id"] is None
    assert result["count"] == 0
    assert result["count_inactive"] == 0
    assert result["synonym"] is False
    assert result["rank"] == FBRank.VARIETY
    assert result["taxonomic_status"] == "Accepted"
    assert result["lsid"] == "urn:lsid:ipni.org:names:77155656-1"
    assert result["custom_suffix"] is None
    assert result["distribution_concat"] == "Northern Provinces (natives)"


@pytest.mark.asyncio()
async def test_save_taxon(
    ac: AsyncClient,
) -> None:
    """Search taxon from earlier test case and save one of the results."""
    payload = {  # FTaxonInfoRequest
        "include_external_apis": True,
        "taxon_name_pattern": "Haworthiopsis koelmaniorum",
        "search_for_genus_not_species": False,
    }
    response = await ac.post("/api/search_taxa_by_name", json=payload)
    assert response.status_code == 200
    taxon = next(
        r
        for r in response.json()["ResultsCollection"]
        if r["name"] == "Haworthiopsis koelmaniorum var. mcmurtryi"
    )

    payload = taxon.copy()  # TaxonCreate
    del payload["name"]
    del payload["in_db"]
    del payload["count"]
    del payload["count_inactive"]

    # save taxon to db
    response = await ac.post("/api/taxa/new", json=payload)
    assert response.status_code == 200
    resp = response.json()
    assert resp["new_taxon"]["name"] == "Haworthiopsis koelmaniorum var. mcmurtryi"
    assert resp["new_taxon"]["id"] is not None

    # read taxon from db
    response = await ac.get(f"/api/taxa/{resp['new_taxon']['id']}")
    assert response.status_code == 200
    resp = response.json()
    assert resp["taxon"]["name"] == "Haworthiopsis koelmaniorum var. mcmurtryi"
    assert resp["taxon"]["id"] is not None


@pytest.mark.asyncio()
async def test_update_taxon(ac: AsyncClient, taxa_in_db: list[Taxon]) -> None:
    taxon_in_db = taxa_in_db[0]
    """Update taxon attribute custom_notes."""
    payload = {  # FModifiedTaxa
        "ModifiedTaxaCollection": [
            {
                "id": taxon_in_db.id,
                "custom_notes": "   has been updated    ",  # to be stripped
            }
        ]
    }
    response = await ac.put("/api/taxa/", json=payload)
    assert response.status_code == 200

    # read taxon from db
    response = await ac.get(f"/api/taxa/{taxon_in_db.id}")
    assert response.status_code == 200
    assert response.json()["taxon"]["custom_notes"] == "has been updated"

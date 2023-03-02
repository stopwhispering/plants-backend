from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from plants.shared.enums import ProposalEntity

if TYPE_CHECKING:
    from httpx import AsyncClient

    from plants.modules.plant.models import Plant
    from plants.modules.taxon.models import Taxon


@pytest.mark.asyncio()
async def test_get_nursery_proposals(ac: AsyncClient, plant_valid_in_db: Plant) -> None:
    response = await ac.get(f"/api/proposals/{ProposalEntity.NURSERY.value}")
    assert response.status_code == 200
    resp = response.json()
    assert len(resp["NurseriesSourcesCollection"]) == 1
    assert (
        resp["NurseriesSourcesCollection"][0]["name"]
        == plant_valid_in_db.nursery_source
    )


@pytest.mark.asyncio()
async def test_get_image_keyword_proposals(
    ac: AsyncClient,
    valid_plant_in_db_with_image: Plant,  # noqa: ARG001
) -> None:
    response = await ac.get(f"/api/proposals/{ProposalEntity.KEYWORD.value}")
    assert response.status_code == 200
    resp = response.json()
    assert len(resp["KeywordsCollection"]) == 2
    assert {"keyword": "new leaf"} in resp["KeywordsCollection"]
    assert {"keyword": "flower"} in resp["KeywordsCollection"]


@pytest.mark.asyncio()
async def test_get_taxon_tree(
    ac: AsyncClient,
    taxon_in_db: Taxon,
    plant_valid_in_db: Plant,
) -> None:
    response = await ac.get("/api/selection_data/")
    assert response.status_code == 200
    resp = response.json()
    assert "Selection" in resp
    assert "TaxonTree" in resp["Selection"]
    assert len(resp["Selection"]["TaxonTree"]) >= 1

    node_family = next(
        t for t in resp["Selection"]["TaxonTree"] if t["key"] == taxon_in_db.family
    )
    node_genus = next(t for t in node_family["nodes"] if t["key"] == taxon_in_db.genus)
    node_species = next(
        t for t in node_genus["nodes"] if t["key"] == taxon_in_db.species
    )
    assert node_species["level"] == 2
    assert node_species["count"] >= 1
    assert plant_valid_in_db.id in node_species["plant_ids"]

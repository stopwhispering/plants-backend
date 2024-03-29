from __future__ import annotations

import pytest

from plants.modules.biodiversity.lookup_gbif_id import lookup_gbif_id


@pytest.mark.asyncio()
async def test_gbif_lookup_via_pygbif() -> None:
    # uses third-party API pygbif and gbif REST API
    gbif_id = await lookup_gbif_id(
        taxon_name="Haworthia truncata var. maughanii",
        lsid="urn:lsid:ipni.org:names:60468368-2",
    )
    assert gbif_id == 8309276


@pytest.mark.asyncio()
async def test_gbif_lookup_via_wikidata() -> None:
    # fails for pygbif; uses wikidata REST API and the wikidata package
    gbif_id = await lookup_gbif_id(
        taxon_name="Haworthia chloracantha var. subglauca",
        lsid="urn:lsid:ipni.org:names:536020-1",
    )
    assert gbif_id == 2779965

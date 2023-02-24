import pytest
from httpx import AsyncClient

from plants.modules.image.image_dal import ImageDAL
from plants.modules.plant.models import Plant
from plants.shared.enums import ProposalEntity


@pytest.mark.asyncio
async def test_get_nursery_proposals(ac: AsyncClient, plant_valid_in_db: Plant):
    response = await ac.get(f"/api/proposals/{ProposalEntity.NURSERY.value}")
    assert response.status_code == 200
    resp = response.json()
    assert len(resp['NurseriesSourcesCollection']) == 1
    assert (resp['NurseriesSourcesCollection'][0]['name'] ==
            plant_valid_in_db.nursery_source)


@pytest.mark.asyncio
async def test_get_image_keyword_proposals(
        ac: AsyncClient,
        valid_plant_in_db_with_image: Plant,
        image_dal: ImageDAL,):
    response = await ac.get(f"/api/proposals/{ProposalEntity.KEYWORD.value}")
    assert response.status_code == 200
    resp = response.json()
    assert len(resp['KeywordsCollection']) == 2
    assert {'keyword': 'new leaf'} in resp['KeywordsCollection']
    assert {'keyword': 'flower'} in resp['KeywordsCollection']


@pytest.mark.asyncio
async def test_get_taxon_tree(
        ac: AsyncClient,
        valid_plant_in_db_with_image: Plant,):
    response = await ac.get("/api/selection_data/")
    assert response.status_code == 200
    resp = response.json()
    assert 'Selection' in resp
    assert 'TaxonTree' in resp['Selection']
    assert len(resp['Selection']['TaxonTree']) >= 1

    # todo more checks after we have taxa in test db

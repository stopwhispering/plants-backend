import pytest
from httpx import AsyncClient

from plants.modules.plant.history_dal import HistoryDAL
from plants.modules.plant.models import Plant


@pytest.mark.asyncio
async def test_untagged_images_empty(ac: AsyncClient):
    response = await ac.get("/api/images/untagged/")
    assert response.status_code == 200
    assert response.json().get('message').get('message') == 'Returned 0 images.'

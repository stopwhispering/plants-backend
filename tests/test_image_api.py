import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_untagged_images_empty(ac: AsyncClient):
    response = await ac.get("/api/images/untagged/")
    assert response.status_code == 200
    assert response.json().get('message').get('message') == 'Returned 0 images.'

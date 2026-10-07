import pytest
from httpx import ASGITransport, AsyncClient

from usurp.main import app


@pytest.mark.asyncio
async def test_search_endpoint_returns_400_on_no_params() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/search")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_endpoint_accepts_query_params() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/search", params={"q": "test"})
    assert response.status_code == 200
    assert "organic_results" in response.json()

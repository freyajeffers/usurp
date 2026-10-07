import pytest
from httpx import ASGITransport, AsyncClient

from usurp.main import app, get_service
from usurp.parser import parse_serp_html


class FakeService:
    async def search(self, request: object, *, no_cache: bool = False) -> object:
        return parse_serp_html("<div id='search'></div>", query="test")


@pytest.fixture(autouse=True)
def override_service() -> None:
    app.dependency_overrides[get_service] = lambda: FakeService()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_endpoint_returns_400_on_no_params() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/search")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_endpoint_returns_normalized_response() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/search", params={"q": "test"})
    assert response.status_code == 200
    assert "organic_results" in response.json()


@pytest.mark.asyncio
async def test_health_endpoint_reports_ready() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_search_requires_configured_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USURP_API_KEY", "expected-secret")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        missing = await ac.get("/search", params={"q": "test"})
        valid = await ac.get("/search", params={"q": "test", "api_key": "expected-secret"})
    assert missing.status_code == 401
    assert valid.status_code == 200

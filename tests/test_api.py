import pytest
from httpx import ASGITransport, AsyncClient

from usurp.escalation import EscalationManager
from usurp.main import app, get_escalation_manager, get_service
from usurp.parser import parse_serp_html


class FakeService:
    async def search(
        self,
        request: object,
        *,
        no_cache: bool = False,
        rate_limit_key: str = "anonymous",
    ) -> object:
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


@pytest.mark.asyncio
async def test_escalation_admin_endpoints_list_and_resolve(tmp_path) -> None:
    manager = EscalationManager(tmp_path)
    manager.create_ticket("ticket-1", "test", "captcha")
    app.dependency_overrides[get_escalation_manager] = lambda: manager
    transport = ASGITransport(app=app)
    html = '<div class="MjjYud"><a href="https://example.test"><h3>Resolved</h3></a></div>'
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listed = await ac.get("/admin/escalations")
        resolved = await ac.post(
            "/admin/escalations/ticket-1/resolve",
            json={"rendered_html": html},
        )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == "ticket-1"
    assert resolved.status_code == 200
    assert resolved.json()["organic_results"][0]["title"] == "Resolved"


@pytest.mark.asyncio
async def test_admin_ui_lists_and_resolves_ticket(tmp_path) -> None:
    manager = EscalationManager(tmp_path)
    manager.create_ticket("ticket-ui", "test", "captcha")
    app.dependency_overrides[get_escalation_manager] = lambda: manager
    transport = ASGITransport(app=app)
    html = '<div class="MjjYud"><a href="https://example.test"><h3>UI result</h3></a></div>'
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        page = await ac.get("/admin/ui")
        resolved = await ac.post(
            "/admin/ui/resolve",
            data={"api_key": "operator", "ticket_id": "ticket-ui"},
            files={"html_file": ("rendered.html", html, "text/html")},
            follow_redirects=False,
        )
    assert page.status_code == 200
    assert "ticket-ui" in page.text
    assert resolved.status_code == 303
    assert manager.get_ticket("ticket-ui")["status"] == "resolved"


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_payload() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/metrics")
    assert response.status_code == 200
    assert "usurp_search_requests_total" in response.text

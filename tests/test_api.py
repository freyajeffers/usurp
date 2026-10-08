import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from usurp.browser import ChallengeType
from usurp.escalation import EscalationManager
from usurp.main import (
    EscalationSubmission,
    app,
    get_escalation_manager,
    get_query,
    get_service,
    resolve_escalation,
)
from usurp.parser import parse_serp_html
from usurp.service import BrowserChallengeError, RateLimitExceededError


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


@pytest.mark.asyncio
async def test_query_dependency_and_service_factory() -> None:
    assert await get_query() is None
    query = await get_query(q="test", start=2, num=5)
    assert query is not None
    assert query.start == 2
    assert get_service() is not None
    assert get_escalation_manager() is not None


@pytest.mark.asyncio
async def test_admin_ui_rejects_bad_upload_and_missing_ticket(tmp_path) -> None:
    manager = EscalationManager(tmp_path)
    app.dependency_overrides[get_escalation_manager] = lambda: manager
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        bad_type = await ac.post(
            "/admin/ui/resolve",
            data={"api_key": "operator", "ticket_id": "missing"},
            files={"html_file": ("input.txt", "data", "text/plain")},
        )
        missing = await ac.post(
            "/admin/ui/resolve",
            data={"api_key": "operator", "ticket_id": "missing"},
            files={"html_file": ("input.html", "<html></html>", "text/html")},
        )
    assert bad_type.status_code == 400
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_rejects_oversized_upload(tmp_path) -> None:
    manager = EscalationManager(tmp_path)
    app.dependency_overrides[get_escalation_manager] = lambda: manager
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/admin/ui/resolve",
            data={"api_key": "operator", "ticket_id": "missing"},
            files={"html_file": ("large.html", "x" * 5_000_001, "text/html")},
        )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_resolve_escalation_maps_missing_and_invalid_ticket(tmp_path) -> None:
    manager = EscalationManager(tmp_path)
    app.dependency_overrides[get_escalation_manager] = lambda: manager
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        missing = await ac.post(
            "/admin/escalations/missing/resolve",
            json={"rendered_html": "<html></html>"},
        )
        invalid = await ac.post(
            "/admin/escalations/../resolve/resolve",
            json={"rendered_html": "<html></html>"},
        )
    assert missing.status_code == 404
    assert invalid.status_code in {400, 404}


@pytest.mark.asyncio
async def test_resolve_escalation_maps_manager_validation_error(tmp_path) -> None:
    manager = EscalationManager(tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        await resolve_escalation(
            "../invalid",
            EscalationSubmission(rendered_html="<html></html>"),
            manager=manager,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_search_maps_rate_limit_and_runtime_errors() -> None:
    class FailingService:
        def __init__(self, error: Exception) -> None:
            self.error = error

        async def search(self, *args, **kwargs):
            raise self.error

    transport = ASGITransport(app=app)
    app.dependency_overrides[get_service] = lambda: FailingService(
        RateLimitExceededError("limited")
    )
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        limited = await ac.get("/search", params={"q": "test"})
    assert limited.status_code == 429

    app.dependency_overrides[get_service] = lambda: FailingService(RuntimeError("down"))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        unavailable = await ac.get("/search", params={"q": "test"})
    assert unavailable.status_code == 503

    app.dependency_overrides[get_service] = lambda: FailingService(
        BrowserChallengeError(ChallengeType.JS_CHALLENGE, ticket_id="ticket")
    )
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        challenged = await ac.get("/search", params={"q": "test"})
    assert challenged.status_code == 503
    assert challenged.json()["detail"]["ticket_id"] == "ticket"

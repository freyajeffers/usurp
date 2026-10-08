from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from usurp.browser import ChallengeType, EscalationRequest, EscalationResult
from usurp.browser.chain import EscalationChain
from usurp.escalation import EscalationManager
from usurp.main import app, get_escalation_manager, get_service
from usurp.service import SearchService
from usurp.transport import TransportRequest, TransportResult

pytestmark = pytest.mark.integration


RESULT_HTML = (
    '<div class="MjjYud"><a href="https://integration.test"><h3>Integration result</h3></a></div>'
)


class IntegrationTransport:
    def __init__(self, *, challenged: bool = False) -> None:
        self.challenged = challenged
        self.calls = 0

    async def fetch(self, request: TransportRequest) -> TransportResult:
        self.calls += 1
        return TransportResult(
            status_code=429 if self.challenged else 200,
            headers={},
            raw_html="captcha" if self.challenged else RESULT_HTML,
            response_time_ms=2.0,
            escalation_required=self.challenged,
        )


class IntegrationEscalator:
    def __init__(self, *, resolved: bool) -> None:
        self.resolved = resolved
        self.calls = 0

    async def execute(self, request: EscalationRequest) -> EscalationResult:
        self.calls += 1
        return EscalationResult(
            rendered_html=RESULT_HTML if self.resolved else "captcha",
            final_url=request.target_url,
            execution_duration_ms=4.0,
            challenge_type_encountered=(
                ChallengeType.NONE if self.resolved else ChallengeType.HARD_CAPTCHA
            ),
            resolved_successfully=self.resolved,
        )


@pytest.fixture(autouse=True)
def clear_app_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_http_search_runs_transport_escalation_parser_and_cache(tmp_path: Path) -> None:
    transport = IntegrationTransport(challenged=True)
    escalator = IntegrationEscalator(resolved=True)
    service = SearchService(
        transport=transport,
        escalator=EscalationChain((escalator,)),
        cache_path=tmp_path / "integration.sqlite3",
    )
    app.dependency_overrides[get_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/search", params={"q": "integration"})
        second = await client.get("/v1/search", params={"q": "integration"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["organic_results"][0]["title"] == "Integration result"
    assert second.json()["organic_results"][0]["link"] == "https://integration.test"
    assert transport.calls == 1
    assert escalator.calls == 1


@pytest.mark.asyncio
async def test_http_search_persists_unresolved_challenge_ticket(tmp_path: Path) -> None:
    transport = IntegrationTransport(challenged=True)
    escalator = IntegrationEscalator(resolved=False)
    manager = EscalationManager(tmp_path / "tickets")
    service = SearchService(transport=transport, escalator=escalator, escalation_manager=manager)
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[get_escalation_manager] = lambda: manager

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/search", params={"q": "needs-review"})
        tickets = await client.get("/admin/escalations")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "browser_challenge_unresolved"
    assert detail["ticket_id"]
    assert tickets.status_code == 200
    assert tickets.json()[0]["query"] == "needs-review"


@pytest.mark.asyncio
async def test_http_search_enforces_api_key_at_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USURP_API_KEY", "integration-secret")
    app.dependency_overrides[get_service] = lambda: SearchService(transport=IntegrationTransport())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.get("/search", params={"q": "protected"})
        valid = await client.get(
            "/search", params={"q": "protected", "api_key": "integration-secret"}
        )

    assert missing.status_code == 401
    assert valid.status_code == 200

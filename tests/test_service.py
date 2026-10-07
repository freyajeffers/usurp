import pytest

from usurp.browser import ChallengeType, EscalationResult
from usurp.service import SearchService
from usurp.transport import TransportRequest, TransportResult


class FakeTransport:
    def __init__(self) -> None:
        self.calls = 0

    async def fetch(self, request: TransportRequest) -> TransportResult:
        self.calls += 1
        return TransportResult(
            status_code=200,
            headers={},
            raw_html='<div class="MjjYud"><a href="https://example.test"><h3>Result</h3></a></div>',
            response_time_ms=1.0,
        )


@pytest.mark.asyncio
async def test_search_service_fetches_parses_and_caches(tmp_path) -> None:
    transport = FakeTransport()
    service = SearchService(transport=transport, cache_path=tmp_path / "cache.db")
    request = TransportRequest(query="test")

    first = await service.search(request)
    second = await service.search(request)

    assert first.organic_results[0].title == "Result"
    assert second.organic_results[0].link == "https://example.test"
    assert transport.calls == 1


@pytest.mark.asyncio
async def test_search_service_rejects_transport_escalation() -> None:
    class ChallengedTransport(FakeTransport):
        async def fetch(self, request: TransportRequest) -> TransportResult:
            return TransportResult(
                status_code=429,
                headers={},
                raw_html="captcha",
                response_time_ms=1.0,
                escalation_required=True,
            )

    service = SearchService(transport=ChallengedTransport())

    with pytest.raises(RuntimeError, match="escalation"):
        await service.search(TransportRequest(query="blocked"))


@pytest.mark.asyncio
async def test_search_service_escalates_challenged_transport() -> None:
    class ChallengedTransport(FakeTransport):
        async def fetch(self, request: TransportRequest) -> TransportResult:
            return TransportResult(
                status_code=429,
                headers={},
                raw_html="captcha",
                response_time_ms=1.0,
                escalation_required=True,
            )

    class FakeEscalator:
        def __init__(self) -> None:
            self.request = None

        async def execute(self, request):
            self.request = request
            return EscalationResult(
                rendered_html='<div class="MjjYud"><a href="https://example.test"><h3>Rendered</h3></a></div>',
                final_url="https://www.google.com/search?q=blocked",
                execution_duration_ms=25.0,
                challenge_type_encountered=ChallengeType.NONE,
                resolved_successfully=True,
            )

    escalator = FakeEscalator()
    service = SearchService(transport=ChallengedTransport(), escalator=escalator)

    response = await service.search(TransportRequest(query="blocked"))

    assert response.organic_results[0].title == "Rendered"
    assert escalator.request is not None
    assert str(escalator.request.target_url) == (
        "https://www.google.com/search?q=blocked&gl=us&hl=en&start=0&num=10&device=desktop"
    )

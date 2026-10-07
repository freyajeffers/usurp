import pytest

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

import pytest

from usurp.browser import ChallengeType, EscalationResult
from usurp.rate_limit import RateLimitPolicy, TokenBucketRateLimiter
from usurp.service import BrowserChallengeError, SearchService
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


@pytest.mark.asyncio
async def test_search_service_rejects_rate_limited_client() -> None:
    limiter = TokenBucketRateLimiter(
        RateLimitPolicy(
            max_requests_per_minute=1,
            burst_capacity=1,
            per_proxy_delay_seconds=0.0,
        )
    )
    service = SearchService(transport=FakeTransport(), rate_limiter=limiter)
    request = TransportRequest(query="limited")

    await service.search(request, rate_limit_key="client-1")
    with pytest.raises(RuntimeError, match="rate limit"):
        await service.search(request, rate_limit_key="client-1", no_cache=True)


@pytest.mark.asyncio
async def test_search_service_rejects_unresolved_browser_challenge() -> None:
    class ChallengedTransport(FakeTransport):
        async def fetch(self, request: TransportRequest) -> TransportResult:
            return TransportResult(
                status_code=429,
                headers={},
                raw_html="captcha",
                response_time_ms=1.0,
                escalation_required=True,
            )

    class UnresolvedEscalator:
        async def execute(self, request):
            return EscalationResult(
                rendered_html="captcha",
                final_url="https://www.google.com/sorry/index",
                execution_duration_ms=100.0,
                challenge_type_encountered=ChallengeType.HARD_CAPTCHA,
                resolved_successfully=False,
            )

    service = SearchService(transport=ChallengedTransport(), escalator=UnresolvedEscalator())

    with pytest.raises(BrowserChallengeError, match="did not resolve") as exc_info:
        await service.search(TransportRequest(query="captcha"))
    assert exc_info.value.challenge_type is ChallengeType.HARD_CAPTCHA

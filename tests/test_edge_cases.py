from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest

from usurp.cache import CacheSettings, SQLiteSerpCache
from usurp.escalation import EscalationManager
from usurp.parser import parse_serp_html
from usurp.providers import (
    GoogleProgrammableSearchProvider,
    GoogleProgrammableSearchSettings,
    OfficialProviderError,
)
from usurp.rate_limit import RateLimitPolicy, TokenBucketRateLimiter
from usurp.transport import TransportRequest


def test_cache_rejects_invalid_ttl() -> None:
    with pytest.raises(ValueError):
        SQLiteSerpCache(Path("/tmp/cache.db"), ttl=timedelta(minutes=1))
    assert CacheSettings(ttl=timedelta(hours=1)).ttl == timedelta(hours=1)
    assert CacheSettings.validate_ttl(timedelta(hours=1)) == timedelta(hours=1)
    with pytest.raises(ValueError):
        CacheSettings.validate_ttl(timedelta(minutes=1))


def test_cache_connection_rolls_back_and_closes_on_error(tmp_path: Path) -> None:
    cache = SQLiteSerpCache(tmp_path / "cache.db")
    with cache._connection() as connection:
        connection.execute("CREATE TABLE rollback_test (value TEXT)")
    with pytest.raises(RuntimeError, match="rollback"), cache._connection() as connection:
        connection.execute("INSERT INTO rollback_test VALUES ('not-committed')")
        raise RuntimeError("rollback")
    with cache._connection() as connection:
        assert connection.execute("SELECT * FROM rollback_test").fetchone() is None


def test_escalation_manager_rejects_bad_ids_and_corrupt_files(tmp_path: Path) -> None:
    manager = EscalationManager(tmp_path)
    with pytest.raises(ValueError):
        manager.create_ticket("../escape", "q", "html")
    (tmp_path / "broken.json").write_text("{")
    (tmp_path / "scalar.json").write_text(json.dumps(["not-a-ticket"]))
    assert manager.list_tickets() == [["not-a-ticket"]]
    with pytest.raises(FileNotFoundError):
        manager.submit_solution("missing", "<html></html>")


def test_parser_covers_fallback_and_invalid_result_nodes() -> None:
    html = """
    <div data-snhf><a href='/relative'><h3>Skip</h3></a></div>
    <div data-snhf><a href='https://valid.test'><h3>Valid</h3><div data-sncf>Snippet</div></a></div>
    <div class='knowledge-panel'><h2>Title</h2><div data-attrid='description'>Desc</div></div>
    <div class='related-question-pair' data-q='Why?'><div>Answer</div></div>
    <div id='botstuff'><a href='/search?q=related'>Related</a><a id='pnnext' href='/search?start=10'>Next</a></div>
    <a id='pnnext' href='/search?start=10'>Next</a>
    """
    result = parse_serp_html(html, query="q", num=10)
    assert result.organic_results[0].title == "Valid"
    assert result.knowledge_graph == {"title": "Title", "description": "Desc"}
    assert result.related_questions == [{"question": "Why?", "answer": "Answer"}]
    assert result.related_searches == [
        {"query": "Related", "link": "https://www.google.com/search?q=related"}
    ]
    assert result.pagination["next"] == "https://www.google.com/search?start=10"
    missing_heading = parse_serp_html(
        '<div class="MjjYud"><a href="https://missing-heading.test">No heading</a></div>',
        query="q",
    )
    assert missing_heading.organic_results == []
    limited = parse_serp_html(
        '<div class="MjjYud"><a href="https://one.test"><h3>One</h3></a></div>'
        '<div class="MjjYud"><a href="https://two.test"><h3>Two</h3></a></div>',
        query="q",
        num=1,
    )
    assert len(limited.organic_results) == 1


class ProviderResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


class ProviderSession:
    def __init__(self, response: ProviderResponse) -> None:
        self.response = response
        self.params = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, endpoint: str, **kwargs: object) -> ProviderResponse:
        self.params = kwargs
        return self.response


@pytest.mark.asyncio
async def test_official_provider_maps_items_and_skips_invalid(monkeypatch) -> None:
    session = ProviderSession(
        ProviderResponse(
            200,
            {"items": [{"title": "ok", "link": "https://ok.test", "snippet": "s"}, {}]},
        )
    )
    provider = GoogleProgrammableSearchProvider(
        GoogleProgrammableSearchSettings(api_key="key", search_engine_id="engine"),
        session_factory=lambda: session,
    )
    result = await provider.search(TransportRequest(query="q", num_results=20))
    assert result.organic_results[0].title == "ok"
    assert session.params["params"]["num"] == 10


@pytest.mark.asyncio
async def test_official_provider_rejects_http_and_payload_errors() -> None:
    request = TransportRequest(query="q")
    provider = GoogleProgrammableSearchProvider(
        GoogleProgrammableSearchSettings(api_key="key", search_engine_id="engine"),
        session_factory=lambda: ProviderSession(ProviderResponse(500, {})),
    )
    with pytest.raises(OfficialProviderError, match="HTTP 500"):
        await provider.search(request)
    invalid = GoogleProgrammableSearchProvider(
        GoogleProgrammableSearchSettings(api_key="key", search_engine_id="engine"),
        session_factory=lambda: ProviderSession(ProviderResponse(200, {"items": {}})),
    )
    with pytest.raises(OfficialProviderError, match="invalid items"):
        await invalid.search(request)


def test_provider_environment_is_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("USURP_GOOGLE_CSE_API_KEY", raising=False)
    monkeypatch.delenv("USURP_GOOGLE_CSE_ID", raising=False)
    assert GoogleProgrammableSearchProvider.from_environment() is None
    monkeypatch.setenv("USURP_GOOGLE_CSE_API_KEY", "key")
    monkeypatch.setenv("USURP_GOOGLE_CSE_ID", "id")
    assert GoogleProgrammableSearchProvider.from_environment() is not None


@pytest.mark.asyncio
async def test_rate_limiter_waits_for_proxy_delay(monkeypatch) -> None:
    limiter = TokenBucketRateLimiter(
        RateLimitPolicy(max_requests_per_minute=60, burst_capacity=2, per_proxy_delay_seconds=1.0)
    )
    await limiter.acquire("proxy")
    assert await limiter.acquire("proxy") is False
    with pytest.raises(ValueError, match="must not be empty"):
        await limiter.acquire("")
    await limiter.reset("proxy")
    assert await limiter.acquire("proxy") is True

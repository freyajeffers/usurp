from types import SimpleNamespace
from uuid import uuid4

import pytest

from usurp.transport import (
    DeviceType,
    FastPathTransport,
    ProxyNode,
    ProxyPoolRouter,
    ProxyProtocol,
    TransportClientSettings,
    TransportRequest,
)


class FakeSession:
    def __init__(self, response: SimpleNamespace) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    async def get(self, url: str, **kwargs: object) -> SimpleNamespace:
        self.calls.append({"url": url, **kwargs})
        return self.response

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_fast_path_builds_google_request_and_maps_response() -> None:
    response = SimpleNamespace(
        status_code=200,
        headers={"Content-Type": "text/html"},
        text="<html>results</html>",
    )
    session = FakeSession(response)
    client = FastPathTransport(
        settings=TransportClientSettings(),
        session_factory=lambda: session,
    )

    result = await client.fetch(TransportRequest(query="quantum error correction"))

    assert result.status_code == 200
    assert result.raw_html == "<html>results</html>"
    assert result.escalation_required is False
    assert session.calls[0]["params"] == {
        "q": "quantum error correction",
        "gl": "us",
        "hl": "en",
        "start": 0,
        "num": 10,
    }
    assert session.calls[0]["impersonate"] == "chrome"
    assert session.calls[0]["timeout"] == (3.0, 5.0)


@pytest.mark.asyncio
async def test_fast_path_flags_captcha_response_for_escalation() -> None:
    response = SimpleNamespace(
        status_code=200,
        headers={},
        text='<html><form action="/sorry/index"></form></html>',
    )
    session = FakeSession(response)
    client = FastPathTransport(session_factory=lambda: session)

    result = await client.fetch(TransportRequest(query="blocked query"))

    assert result.escalation_required is True


@pytest.mark.asyncio
async def test_fast_path_passes_proxy_and_generates_proxy_id() -> None:
    proxy_id = uuid4()
    response = SimpleNamespace(status_code=429, headers={}, text="rate limited")
    session = FakeSession(response)
    client = FastPathTransport(session_factory=lambda: session)

    result = await client.fetch(
        TransportRequest(query="test"),
        proxy_url="http://proxy.example.test:8080",
        proxy_id=proxy_id,
    )

    assert result.proxy_used_id == proxy_id
    assert session.calls[0]["proxy"] == "http://proxy.example.test:8080"
    assert result.escalation_required is True


@pytest.mark.asyncio
async def test_fast_path_selects_and_reports_to_proxy_pool() -> None:
    node = ProxyNode(
        id=uuid4(),
        uri="https://proxy-us.example.test:443",
        protocol=ProxyProtocol.HTTPS,
        region="US",
    )
    pool = ProxyPoolRouter([node])
    response = SimpleNamespace(status_code=200, headers={}, text="<html>results</html>")
    session = FakeSession(response)
    client = FastPathTransport(session_factory=lambda: session, proxy_pool=pool)

    result = await client.fetch(TransportRequest(query="test", session_id="session-1"))

    assert result.proxy_used_id == node.id
    assert session.calls[0]["proxy"] == str(node.uri)
    assert node.avg_latency_ms >= 0


@pytest.mark.asyncio
async def test_mobile_requests_include_mobile_user_agent_and_consent_cookie() -> None:
    response = SimpleNamespace(status_code=200, headers={}, text="<html>results</html>")
    session = FakeSession(response)
    client = FastPathTransport(session_factory=lambda: session)

    await client.fetch(TransportRequest(query="test", device_type=DeviceType.MOBILE))

    headers = session.calls[0]["headers"]
    assert isinstance(headers, dict)
    assert "Mobile" in headers["User-Agent"]
    assert headers["Cookie"] == "CONSENT=PENDING+987; SOCS=CAESHAgCEhJnd3NfMjAyMzAxMjAx"


@pytest.mark.asyncio
async def test_fast_path_includes_time_range_parameter() -> None:
    response = SimpleNamespace(status_code=200, headers={}, text="<html>results</html>")
    session = FakeSession(response)
    client = FastPathTransport(session_factory=lambda: session)
    await client.fetch(TransportRequest(query="test", time_range="qdr:w"))
    assert session.calls[0]["params"]["tbs"] == "qdr:w"

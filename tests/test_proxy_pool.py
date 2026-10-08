from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from usurp.transport import ProxyNode, ProxyPoolRouter, ProxyProtocol


def proxy(region: str, *, failures: int = 0) -> ProxyNode:
    return ProxyNode(
        id=uuid4(),
        uri=f"https://proxy-{region.lower()}.example.test:443",
        protocol=ProxyProtocol.HTTPS,
        region=region,
        consecutive_failures=failures,
    )


@pytest.mark.asyncio
async def test_router_prefers_requested_region_and_tracks_sticky_session() -> None:
    us_node = proxy("US")
    de_node = proxy("DE")
    router = ProxyPoolRouter([us_node, de_node])

    selected = await router.select(region="DE", session_id="session-1")
    repeated = await router.select(region="US", session_id="session-1")

    assert selected is de_node
    assert repeated is de_node


@pytest.mark.asyncio
async def test_router_quarantines_rate_limited_proxy_and_fails_over() -> None:
    first = proxy("US")
    second = proxy("US")
    router = ProxyPoolRouter([first, second], base_cooldown_seconds=60.0)

    await router.record_result(first.id, status_code=429, response_time_ms=800.0)
    selected = await router.select(region="US")

    assert first.is_active is False
    assert first.quarantined_until is not None
    assert selected is second
    assert first.consecutive_failures == 1


@pytest.mark.asyncio
async def test_router_reactivates_expired_quarantine() -> None:
    node = proxy("US")
    router = ProxyPoolRouter([node], base_cooldown_seconds=1.0)

    await router.record_result(node.id, status_code=403, response_time_ms=100.0)
    assert await router.select(region="US") is None

    assert node.quarantined_until is not None
    node.quarantined_until = datetime.now(UTC) - timedelta(seconds=1)
    selected = await router.select(region="US")

    assert selected is node
    assert node.is_active is True


@pytest.mark.asyncio
async def test_router_success_resets_failures_and_updates_latency() -> None:
    node = proxy("US", failures=2)
    router = ProxyPoolRouter([node])

    await router.record_result(node.id, status_code=200, response_time_ms=42.5)

    assert node.consecutive_failures == 0
    assert node.is_active is True
    assert node.avg_latency_ms == 42.5


def test_router_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="positive"):
        ProxyPoolRouter([], base_cooldown_seconds=0)


@pytest.mark.asyncio
async def test_router_rejects_invalid_result_updates() -> None:
    node = proxy("US")
    router = ProxyPoolRouter([node])
    with pytest.raises(ValueError, match="non-negative"):
        await router.record_result(node.id, status_code=200, response_time_ms=-1)
    with pytest.raises(KeyError, match="unknown proxy"):
        await router.record_result(uuid4(), status_code=200, response_time_ms=1)

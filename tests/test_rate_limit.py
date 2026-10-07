import asyncio

import pytest

from usurp.rate_limit import RateLimitPolicy, TokenBucketRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_burst_then_rejects() -> None:
    limiter = TokenBucketRateLimiter(
        RateLimitPolicy(max_requests_per_minute=60, burst_capacity=2, per_proxy_delay_seconds=0.0)
    )

    assert await limiter.acquire("client") is True
    assert await limiter.acquire("client") is True
    assert await limiter.acquire("client") is False


@pytest.mark.asyncio
async def test_rate_limiter_isolates_keys() -> None:
    limiter = TokenBucketRateLimiter(
        RateLimitPolicy(max_requests_per_minute=60, burst_capacity=1, per_proxy_delay_seconds=0.0)
    )

    assert await limiter.acquire("client-a") is True
    assert await limiter.acquire("client-a") is False
    assert await limiter.acquire("client-b") is True


@pytest.mark.asyncio
async def test_rate_limiter_enforces_proxy_delay() -> None:
    limiter = TokenBucketRateLimiter(
        RateLimitPolicy(
            max_requests_per_minute=6000, burst_capacity=10, per_proxy_delay_seconds=0.05
        )
    )

    assert await limiter.acquire("proxy") is True
    assert await limiter.acquire("proxy") is False
    await asyncio.sleep(0.06)
    assert await limiter.acquire("proxy") is True

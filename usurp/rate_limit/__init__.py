import asyncio
from time import monotonic

from pydantic import BaseModel, ConfigDict, Field


class RateLimitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    max_requests_per_minute: int = Field(gt=0)
    burst_capacity: int = Field(gt=0)
    per_proxy_delay_seconds: float = Field(ge=0.0)


class TokenBucketRateLimiter:
    """Async token buckets keyed by client or proxy identifier."""

    def __init__(self, policy: RateLimitPolicy) -> None:
        self._policy = policy
        self._refill_per_second = policy.max_requests_per_minute / 60.0
        self._buckets: dict[str, tuple[float, float, float]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> bool:
        if not key:
            raise ValueError("rate-limit key must not be empty")
        async with self._lock:
            now = monotonic()
            tokens, updated_at, last_grant = self._buckets.get(
                key, (float(self._policy.burst_capacity), now, float("-inf"))
            )
            tokens = min(
                float(self._policy.burst_capacity),
                tokens + (now - updated_at) * self._refill_per_second,
            )
            if now - last_grant < self._policy.per_proxy_delay_seconds or tokens < 1.0:
                self._buckets[key] = (tokens, now, last_grant)
                return False
            self._buckets[key] = (tokens - 1.0, now, now)
            return True

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._buckets.pop(key, None)


__all__ = ["RateLimitPolicy", "TokenBucketRateLimiter"]

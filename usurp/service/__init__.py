from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode

from pydantic import HttpUrl, TypeAdapter

from usurp.browser import EscalationRequest, EscalationResult
from usurp.cache import SQLiteSerpCache
from usurp.parser import SerpApiResponse, parse_serp_html
from usurp.transport import TransportRequest, TransportResult


class TransportProtocol(Protocol):
    def fetch(self, request: TransportRequest) -> Awaitable[TransportResult]: ...


class BrowserEscalatorProtocol(Protocol):
    def execute(self, request: EscalationRequest) -> Awaitable[EscalationResult]: ...


class RateLimiterProtocol(Protocol):
    def acquire(self, key: str) -> Awaitable[bool]: ...


class RateLimitExceededError(RuntimeError):
    """Raised when a client has exhausted its configured request budget."""


class SearchService:
    """Coordinates transport, challenge detection, parsing, and optional caching."""

    def __init__(
        self,
        *,
        transport: TransportProtocol,
        cache_path: Path | None = None,
        cache_factory: Callable[[Path], SQLiteSerpCache] = SQLiteSerpCache,
        escalator: BrowserEscalatorProtocol | None = None,
        rate_limiter: RateLimiterProtocol | None = None,
    ) -> None:
        self._transport = transport
        self._escalator = escalator
        self._rate_limiter = rate_limiter
        self._cache = cache_factory(cache_path) if cache_path is not None else None

    async def search(
        self,
        request: TransportRequest,
        *,
        no_cache: bool = False,
        rate_limit_key: str = "anonymous",
    ) -> SerpApiResponse:
        if self._rate_limiter is not None and not await self._rate_limiter.acquire(rate_limit_key):
            raise RateLimitExceededError("rate limit exceeded")
        parameters = {
            "q": request.query,
            "gl": request.country_code,
            "hl": request.language_code,
            "start": request.start_offset,
            "num": request.num_results,
            "device": request.device_type.value,
        }
        if self._cache is not None and not no_cache:
            cached = await self._cache.get(parameters)
            if cached is not None:
                return cached

        result = await self._transport.fetch(request)
        raw_html = result.raw_html
        if result.escalation_required:
            if self._escalator is None:
                raise RuntimeError("transport requires browser escalation")
            escalation = await self._escalator.execute(self._build_escalation_request(request))
            if not escalation.resolved_successfully:
                raise RuntimeError("browser escalation did not resolve the challenge")
            raw_html = escalation.rendered_html
        response = parse_serp_html(
            raw_html,
            query=request.query,
            country_code=request.country_code,
            language_code=request.language_code,
            start=request.start_offset,
            num=request.num_results,
            device=request.device_type.value,
        )
        if self._cache is not None and not no_cache:
            await self._cache.set(parameters, response)
        return response

    @staticmethod
    def _build_escalation_request(request: TransportRequest) -> EscalationRequest:
        query = urlencode(
            {
                "q": request.query,
                "gl": request.country_code,
                "hl": request.language_code,
                "start": request.start_offset,
                "num": request.num_results,
                "device": request.device_type.value,
            }
        )
        return EscalationRequest(
            target_url=TypeAdapter(HttpUrl).validate_python(
                f"https://www.google.com/search?{query}"
            ),
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            viewport_width=1280,
            viewport_height=900,
        )


__all__ = ["RateLimitExceededError", "SearchService"]

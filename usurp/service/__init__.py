from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol

from usurp.cache import SQLiteSerpCache
from usurp.parser import SerpApiResponse, parse_serp_html
from usurp.transport import TransportRequest, TransportResult


class TransportProtocol(Protocol):
    def fetch(self, request: TransportRequest) -> Awaitable[TransportResult]: ...


class SearchService:
    """Coordinates transport, challenge detection, parsing, and optional caching."""

    def __init__(
        self,
        *,
        transport: TransportProtocol,
        cache_path: Path | None = None,
        cache_factory: Callable[[Path], SQLiteSerpCache] = SQLiteSerpCache,
    ) -> None:
        self._transport = transport
        self._cache = cache_factory(cache_path) if cache_path is not None else None

    async def search(self, request: TransportRequest, *, no_cache: bool = False) -> SerpApiResponse:
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
        if result.escalation_required:
            raise RuntimeError("transport requires browser escalation")
        response = parse_serp_html(
            result.raw_html,
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


__all__ = ["SearchService"]

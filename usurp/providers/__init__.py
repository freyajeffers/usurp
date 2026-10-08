from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from curl_cffi.requests import AsyncSession
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter

from usurp.parser import OrganicResult, SearchMetadata, SearchParameters, SerpApiResponse
from usurp.transport import TransportRequest


class OfficialProviderError(RuntimeError):
    """Raised when the configured official search provider cannot respond."""


class SearchProvider(Protocol):
    async def search(self, request: TransportRequest) -> SerpApiResponse: ...


class GoogleProgrammableSearchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    api_key: str = Field(min_length=1)
    search_engine_id: str = Field(min_length=1)
    endpoint: HttpUrl = TypeAdapter(HttpUrl).validate_python(
        "https://www.googleapis.com/customsearch/v1"
    )


class GoogleProgrammableSearchProvider:
    """Official Google Programmable Search JSON API adapter.

    Credentials are read from the caller/configuration and never logged.
    The provider is opt-in; constructing it from environment variables returns
    ``None`` when either required credential is absent.
    """

    def __init__(
        self,
        settings: GoogleProgrammableSearchSettings,
        session_factory: Callable[[], AsyncSession] = AsyncSession,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory

    @classmethod
    def from_environment(cls) -> GoogleProgrammableSearchProvider | None:
        api_key = os.getenv("USURP_GOOGLE_CSE_API_KEY")
        engine_id = os.getenv("USURP_GOOGLE_CSE_ID")
        if not api_key or not engine_id:
            return None
        return cls(GoogleProgrammableSearchSettings(api_key=api_key, search_engine_id=engine_id))

    async def search(self, request: TransportRequest) -> SerpApiResponse:
        params = {
            "key": self._settings.api_key,
            "cx": self._settings.search_engine_id,
            "q": request.query,
            "start": request.start_offset + 1,
            "num": min(request.num_results, 10),
            "hl": request.language_code,
            "gl": request.country_code,
        }
        async with self._session_factory() as session:
            response = await session.get(str(self._settings.endpoint), params=params, timeout=10)
            if response.status_code != 200:
                raise OfficialProviderError(
                    f"official provider returned HTTP {response.status_code}"
                )
            payload = response.json()
        return self._to_serp_response(payload, request)

    @staticmethod
    def _to_serp_response(payload: dict[str, Any], request: TransportRequest) -> SerpApiResponse:
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise OfficialProviderError("official provider returned an invalid items payload")
        organic: list[OrganicResult] = []
        for position, item in enumerate(items, start=1):
            if not isinstance(item, dict) or not item.get("title") or not item.get("link"):
                continue
            organic.append(
                OrganicResult(
                    position=position,
                    title=str(item["title"]),
                    link=str(item["link"]),
                    displayed_link=str(item.get("displayLink", "")),
                    snippet=str(item.get("snippet", "")),
                )
            )
        now = datetime.now(UTC).isoformat()
        return SerpApiResponse(
            search_metadata=SearchMetadata(
                id=str(uuid4()),
                status="Success",
                created_at=now,
                processed_at=now,
                total_time_taken=0.0,
                google_url="https://www.google.com/search",
            ),
            search_parameters=SearchParameters(
                q=request.query,
                gl=request.country_code,
                hl=request.language_code,
                start=request.start_offset,
                num=request.num_results,
                device=request.device_type.value,
            ),
            organic_results=organic,
            pagination={},
        )


__all__ = [
    "GoogleProgrammableSearchProvider",
    "GoogleProgrammableSearchSettings",
    "OfficialProviderError",
    "SearchProvider",
]

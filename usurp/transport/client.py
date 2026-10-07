from collections.abc import Callable
from time import monotonic
from typing import Any, Protocol, cast
from uuid import UUID

from curl_cffi.requests import AsyncSession
from pydantic import BaseModel, ConfigDict, Field

from .models import TransportRequest, TransportResult


class TransportClientSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    connect_timeout_seconds: float = Field(default=3.0, gt=0.0)
    read_timeout_seconds: float = Field(default=5.0, gt=0.0)
    impersonate: str = "chrome"
    google_url: str = "https://www.google.com/search"


class AsyncSessionProtocol(Protocol):
    async def get(self, url: str, **kwargs: Any) -> Any: ...

    async def close(self) -> None: ...


class FastPathTransport:
    """Minimal Phase 1 HTTP fast path with challenge detection."""

    def __init__(
        self,
        settings: TransportClientSettings | None = None,
        session_factory: Callable[[], AsyncSessionProtocol] | None = None,
    ) -> None:
        self._settings = settings or TransportClientSettings()
        self._session_factory = session_factory or (
            lambda: cast(AsyncSessionProtocol, AsyncSession())
        )

    async def fetch(
        self,
        request: TransportRequest,
        *,
        proxy_url: str | None = None,
        proxy_id: UUID | None = None,
    ) -> TransportResult:
        params = {
            "q": request.query,
            "gl": request.country_code,
            "hl": request.language_code,
            "start": request.start_offset,
            "num": request.num_results,
        }
        if request.time_range is not None:
            params["tbs"] = request.time_range

        request_kwargs: dict[str, Any] = {
            "params": params,
            "impersonate": self._settings.impersonate,
            "timeout": (
                self._settings.connect_timeout_seconds,
                self._settings.read_timeout_seconds,
            ),
        }
        if proxy_url is not None:
            request_kwargs["proxy"] = proxy_url

        session = self._session_factory()
        started = monotonic()
        try:
            response = await session.get(self._settings.google_url, **request_kwargs)
            raw_html = str(response.text)
            headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
            status_code = int(response.status_code)
        finally:
            await session.close()

        return TransportResult(
            status_code=status_code,
            headers=headers,
            raw_html=raw_html,
            response_time_ms=(monotonic() - started) * 1000,
            proxy_used_id=proxy_id,
            escalation_required=self._requires_escalation(status_code, raw_html),
        )

    @staticmethod
    def _requires_escalation(status_code: int, raw_html: str) -> bool:
        if status_code in {403, 429, 503}:
            return True
        body = raw_html.casefold()
        return any(
            marker in body
            for marker in (
                "/sorry/index",
                "recaptcha",
                "captcha",
                "unusual traffic",
                "before you continue to google",
            )
        )

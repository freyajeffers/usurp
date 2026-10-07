from collections.abc import Callable
from time import monotonic
from typing import Any, Protocol, cast
from uuid import UUID

from curl_cffi.requests import AsyncSession
from pydantic import BaseModel, ConfigDict, Field

from ..browser import ChallengeType, detect_challenge
from .models import DeviceType, TransportRequest, TransportResult
from .proxy_pool import ProxyPoolRouter


class TransportClientSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    connect_timeout_seconds: float = Field(default=3.0, gt=0.0)
    read_timeout_seconds: float = Field(default=5.0, gt=0.0)
    impersonate: str = "chrome"
    google_url: str = "https://www.google.com/search"
    desktop_user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
    )
    mobile_user_agent: str = (
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/131.0.0.0 Mobile Safari/537.36"
    )
    consent_cookie: str = "CONSENT=PENDING+987; SOCS=CAESHAgCEhJnd3NfMjAyMzAxMjAx"


class AsyncSessionProtocol(Protocol):
    async def get(self, url: str, **kwargs: Any) -> Any: ...

    async def close(self) -> None: ...


class FastPathTransport:
    """Minimal Phase 1 HTTP fast path with challenge detection."""

    def __init__(
        self,
        settings: TransportClientSettings | None = None,
        session_factory: Callable[[], AsyncSessionProtocol] | None = None,
        proxy_pool: ProxyPoolRouter | None = None,
    ) -> None:
        self._settings = settings or TransportClientSettings()
        self._session_factory = session_factory or (
            lambda: cast(AsyncSessionProtocol, AsyncSession())
        )
        self._proxy_pool = proxy_pool

    async def fetch(
        self,
        request: TransportRequest,
        *,
        proxy_url: str | None = None,
        proxy_id: UUID | None = None,
    ) -> TransportResult:
        if self._proxy_pool is not None and proxy_url is None:
            selected = await self._proxy_pool.select(
                region=request.country_code.upper(),
                session_id=request.session_id,
            )
            if selected is not None:
                proxy_url = str(selected.uri)
                proxy_id = selected.id

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
            "headers": {
                "User-Agent": (
                    self._settings.mobile_user_agent
                    if request.device_type is DeviceType.MOBILE
                    else self._settings.desktop_user_agent
                ),
                "Cookie": self._settings.consent_cookie,
            },
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

        result = TransportResult(
            status_code=status_code,
            headers=headers,
            raw_html=raw_html,
            response_time_ms=(monotonic() - started) * 1000,
            proxy_used_id=proxy_id,
            escalation_required=self._requires_escalation(status_code, raw_html),
        )
        if self._proxy_pool is not None and proxy_id is not None:
            await self._proxy_pool.record_result(
                proxy_id,
                status_code=result.status_code,
                response_time_ms=result.response_time_ms,
            )
        return result

    @staticmethod
    def _requires_escalation(status_code: int, raw_html: str) -> bool:
        return (
            status_code in {403, 429, 503} or detect_challenge(raw_html) is not ChallengeType.NONE
        )

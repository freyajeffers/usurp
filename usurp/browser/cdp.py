from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlsplit

from pydantic import HttpUrl, TypeAdapter

from usurp.browser import ChallengeType, EscalationRequest, EscalationResult, detect_challenge


class CdpEscalator:
    """Optional Chromium CDP escalator for an already running browser."""

    def __init__(self, runner: Any | None = None, cdp_endpoint: str | None = None) -> None:
        self._runner = runner
        self._cdp_endpoint = cdp_endpoint

    async def execute(self, request: EscalationRequest) -> EscalationResult:
        if self._runner is not None:
            return cast(EscalationResult, await self._runner(request))
        if not self._cdp_endpoint:
            return self._unavailable(request)

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return self._unavailable(request)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.connect_over_cdp(self._cdp_endpoint)
                context = await browser.new_context(
                    user_agent=request.user_agent,
                    viewport={"width": request.viewport_width, "height": request.viewport_height},
                )
                page = await context.new_page()
                await page.goto(
                    str(request.target_url),
                    wait_until="domcontentloaded",
                    timeout=int(request.timeout_seconds * 1000),
                )
                html = await page.content()
                challenge = detect_challenge(html)
                return EscalationResult(
                    rendered_html=html,
                    final_url=TypeAdapter(HttpUrl).validate_python(page.url),
                    execution_duration_ms=0.0,
                    challenge_type_encountered=challenge,
                    resolved_successfully=challenge is ChallengeType.NONE,
                )
        except Exception:  # noqa: BLE001 - CDP is optional; chain must continue
            return self._unavailable(request)

    @staticmethod
    def _unavailable(request: EscalationRequest) -> EscalationResult:
        return EscalationResult(
            rendered_html="",
            final_url=TypeAdapter(HttpUrl).validate_python(str(request.target_url)),
            execution_duration_ms=0.0,
            challenge_type_encountered=ChallengeType.JS_CHALLENGE,
            resolved_successfully=False,
        )

    @staticmethod
    def proxy_server(request: EscalationRequest) -> str | None:
        if request.proxy_uri is None:
            return None
        parsed = urlsplit(str(request.proxy_uri))
        if parsed.hostname is None or parsed.port is None:
            raise ValueError("proxy URI must include a host and port")
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"


__all__ = ["CdpEscalator"]

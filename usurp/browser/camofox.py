from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

from pydantic import HttpUrl, TypeAdapter

from usurp.browser import ChallengeType, EscalationRequest, EscalationResult, detect_challenge


class CamofoxEscalator:
    """Camoufox-backed browser escalator with Playwright fallback.

    Camoufox renders pages with a Firefox-based browser profile. It does not
    solve CAPTCHA challenges; unresolved challenges go to human review.
    """

    def __init__(
        self,
        runner: Callable[[EscalationRequest], Awaitable[EscalationResult]] | None = None,
    ) -> None:
        self._runner = runner

    async def execute(self, request: EscalationRequest) -> EscalationResult:
        if self._runner is not None:
            return await self._runner(request)
        try:
            from camoufox.async_api import AsyncCamoufox
        except ImportError:
            from usurp.browser import PlaywrightEscalator

            return await PlaywrightEscalator().execute(request)

        proxy = self.proxy_server(request)
        launch_options: dict[str, object] = {
            "headless": True,
            "humanize": True,
            "window": (request.viewport_width, request.viewport_height),
        }
        if proxy is not None:
            launch_options["proxy"] = {"server": proxy}

        camoufox_factory: Any = AsyncCamoufox
        async with camoufox_factory(**launch_options) as browser:
            page = await browser.new_page()
            await page.set_viewport_size(
                {"width": request.viewport_width, "height": request.viewport_height}
            )
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

    @staticmethod
    def proxy_server(request: EscalationRequest) -> str | None:
        if request.proxy_uri is None:
            return None
        parsed = urlsplit(str(request.proxy_uri))
        if parsed.hostname is None or parsed.port is None:
            raise ValueError("proxy URI must include a host and port")
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"


__all__ = ["CamofoxEscalator"]

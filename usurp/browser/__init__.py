import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter


class ChallengeType(StrEnum):
    NONE = "none"
    CONSENT_DIALOG = "consent_dialog"
    JS_CHALLENGE = "js_challenge"
    HARD_CAPTCHA = "hard_captcha"


class EscalationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    target_url: HttpUrl
    proxy_uri: HttpUrl | None = None
    user_agent: str = Field(min_length=1, max_length=2048)
    viewport_width: int = Field(gt=0, le=7680)
    viewport_height: int = Field(gt=0, le=7680)
    timeout_seconds: float = Field(default=8.0, gt=0.0, le=60.0)


class EscalationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    rendered_html: str
    final_url: HttpUrl
    execution_duration_ms: float = Field(ge=0.0)
    challenge_type_encountered: ChallengeType
    resolved_successfully: bool


def detect_challenge(raw_html: str) -> ChallengeType:
    body = raw_html.casefold()
    if "recaptcha" in body or "hcaptcha" in body or "captcha" in body:
        return ChallengeType.HARD_CAPTCHA
    if "before you continue to google" in body or "consent.google.com" in body:
        return ChallengeType.CONSENT_DIALOG
    if (
        "/sorry/index" in body
        or "unusual traffic" in body
        or "jschl-answer" in body
        or "enablejs" in body
    ):
        return ChallengeType.JS_CHALLENGE
    return ChallengeType.NONE


class PlaywrightEscalator:
    def __init__(
        self,
        runner: Callable[[EscalationRequest], Awaitable[EscalationResult]] | None = None,
    ) -> None:
        self._runner = runner

    async def execute(self, request: EscalationRequest) -> EscalationResult:
        if self._runner is not None:
            return await self._runner(request)
        return await self._execute_playwright(request)

    @staticmethod
    def proxy_server(request: EscalationRequest) -> str | None:
        if request.proxy_uri is None:
            return None
        parsed = urlsplit(str(request.proxy_uri))
        if parsed.hostname is None or parsed.port is None:
            raise ValueError("proxy URI must include a host and port")
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"

    async def _execute_playwright(self, request: EscalationRequest) -> EscalationResult:
        started = time.monotonic()
        proxy = self.proxy_server(request)
        launch_options: dict[str, Any] = {"headless": True}
        if proxy is not None:
            launch_options["proxy"] = {"server": proxy}
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**launch_options)
            try:
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
                initial_html = await page.content()
                challenge = detect_challenge(initial_html)
                if challenge is ChallengeType.CONSENT_DIALOG:
                    for label in ("Reject all", "Accept all"):
                        try:
                            await page.get_by_role("button", name=label).first.click(timeout=1000)
                            break
                        except PlaywrightError:
                            continue
                html = await page.content()
                return EscalationResult(
                    rendered_html=html,
                    final_url=TypeAdapter(HttpUrl).validate_python(page.url),
                    execution_duration_ms=(time.monotonic() - started) * 1000,
                    challenge_type_encountered=challenge,
                    resolved_successfully=detect_challenge(html) is ChallengeType.NONE,
                )
            finally:
                await browser.close()


__all__ = [
    "ChallengeType",
    "EscalationRequest",
    "EscalationResult",
    "PlaywrightEscalator",
    "detect_challenge",
]

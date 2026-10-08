from __future__ import annotations

import sys
import types

import pytest

from usurp.browser import ChallengeType, EscalationRequest
from usurp.browser.camofox import CamofoxEscalator
from usurp.browser.cdp import CdpEscalator


def request(proxy: str | None = None) -> EscalationRequest:
    return EscalationRequest(
        target_url="https://example.test/",
        proxy_uri=proxy,
        user_agent="UA",
        viewport_width=800,
        viewport_height=600,
    )


class Page:
    url = "https://example.test/"

    async def set_viewport_size(self, viewport: dict[str, int]) -> None:
        self.viewport = viewport

    async def goto(self, url: str, wait_until: str, timeout: int) -> None:
        self.url = url

    async def content(self) -> str:
        return "<div>rendered</div>"


class Browser:
    def __init__(self) -> None:
        self.page = Page()

    async def new_page(self) -> Page:
        return self.page

    async def new_context(self, user_agent: str, viewport: dict[str, int]) -> BrowserContext:
        return BrowserContext(self)


class BrowserContext:
    def __init__(self, browser: Browser) -> None:
        self.browser = browser

    async def __aenter__(self) -> Browser:
        return self.browser

    async def new_page(self) -> Page:
        return self.browser.page

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_camofox_executes_fake_browser(monkeypatch) -> None:
    browser = Browser()

    class AsyncCamoufox:
        def __init__(self, **options):
            self.options = options

        async def __aenter__(self):
            return browser

        async def __aexit__(self, exc_type, exc, tb):
            return False

    camoufox_pkg = types.ModuleType("camoufox")
    camoufox_api = types.ModuleType("camoufox.async_api")
    camoufox_api.AsyncCamoufox = AsyncCamoufox
    monkeypatch.setitem(sys.modules, "camoufox", camoufox_pkg)
    monkeypatch.setitem(sys.modules, "camoufox.async_api", camoufox_api)

    result = await CamofoxEscalator().execute(request("http://proxy.example:8080"))
    assert result.resolved_successfully is True
    assert result.challenge_type_encountered is ChallengeType.NONE
    assert browser.page.viewport == {"width": 800, "height": 600}


@pytest.mark.asyncio
async def test_camofox_falls_back_to_playwright_when_unavailable(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "camoufox.async_api", None)
    from usurp import browser

    class Fallback:
        async def execute(self, actual_request):
            return types.SimpleNamespace(resolved_successfully=True)

    monkeypatch.setattr(browser, "PlaywrightEscalator", Fallback)
    result = await CamofoxEscalator().execute(request())
    assert result.resolved_successfully is True


@pytest.mark.asyncio
async def test_cdp_executes_fake_browser(monkeypatch) -> None:
    browser = Browser()

    class Chromium:
        async def connect_over_cdp(self, endpoint: str):
            return browser

    class Playwright:
        chromium = Chromium()

    class Context:
        async def __aenter__(self):
            return Playwright()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    import playwright.async_api as api

    monkeypatch.setattr(api, "async_playwright", lambda: Context())
    result = await CdpEscalator(cdp_endpoint="http://127.0.0.1:9222").execute(request())
    assert result.resolved_successfully is True
    assert result.rendered_html == "<div>rendered</div>"


@pytest.mark.asyncio
async def test_cdp_returns_unavailable_when_playwright_import_fails(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "playwright.async_api", None)
    result = await CdpEscalator(cdp_endpoint="http://127.0.0.1:9222").execute(request())
    assert result.resolved_successfully is False


@pytest.mark.asyncio
async def test_cdp_returns_unavailable_when_connection_fails(monkeypatch) -> None:
    class BadChromium:
        async def connect_over_cdp(self, endpoint: str):
            raise RuntimeError("connection refused")

    class BadPlaywright:
        chromium = BadChromium()

    class Context:
        async def __aenter__(self):
            return BadPlaywright()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    import playwright.async_api as api

    monkeypatch.setattr(api, "async_playwright", lambda: Context())
    result = await CdpEscalator(cdp_endpoint="http://127.0.0.1:9222").execute(request())
    assert result.resolved_successfully is False


def test_browser_backends_reject_proxy_without_port() -> None:
    invalid = EscalationRequest.model_construct(
        target_url="https://example.test/",
        proxy_uri="http://proxy.example",
        user_agent="UA",
        viewport_width=800,
        viewport_height=600,
    )
    with pytest.raises(ValueError, match="host and port"):
        CamofoxEscalator.proxy_server(invalid)
    with pytest.raises(ValueError, match="host and port"):
        CdpEscalator.proxy_server(invalid)


def test_browser_backends_allow_no_proxy() -> None:
    assert CamofoxEscalator.proxy_server(request()) is None
    assert CdpEscalator.proxy_server(request()) is None

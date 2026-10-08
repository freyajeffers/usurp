import pytest
from playwright.async_api import Error as PlaywrightError

from usurp.browser import ChallengeType, EscalationRequest, EscalationResult, PlaywrightEscalator


class FakePage:
    def __init__(self, initial_html: str, after_click_html: str | None = None):
        self._initial = initial_html
        self._after = after_click_html or initial_html
        self.url = "https://example.test/"

    async def goto(self, url: str, wait_until: str, timeout: int) -> None:
        self.url = url

    async def content(self) -> str:
        # return initial first call, then after_click on second
        if hasattr(self, "_was_called"):
            return self._after
        self._was_called = True
        return self._initial

    def get_by_role(self, role: str, name: str):
        class Btn:
            def __init__(self, name: str):
                self.name = name

            async def click(self, timeout: int = 1000):
                return None

            @property
            def first(self):
                return self

        return Btn(name)


class FakeContext:
    def __init__(self, page: FakePage):
        self._page = page

    async def new_page(self):
        return self._page


class FakeBrowser:
    def __init__(self, page: FakePage):
        self._page = page
        self.closed = False

    async def new_context(self, user_agent: str, viewport: dict[str, int]):
        return FakeContext(self._page)

    async def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, page: FakePage):
        self.page = page

    async def launch(self, **kwargs):
        return FakeBrowser(self.page)


class FakePlaywright:
    def __init__(self, page: FakePage):
        self.chromium = FakeChromium(page)


class FakeAsyncPlaywright:
    def __init__(self, page: FakePage):
        self._page = page

    async def __aenter__(self):
        return FakePlaywright(self._page)

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_playwright_escalator_handles_consent_dialog(monkeypatch):
    # initial html contains consent text so detect_challenge returns CONSENT_DIALOG
    initial = "Before you continue to Google <button>Reject all</button>"
    # after click, page returns normal results
    after = "<div>final</div>"
    page = FakePage(initial_html=initial, after_click_html=after)

    # patch async_playwright in the usurp.browser module to return our fake
    import usurp.browser as browser_mod

    monkeypatch.setattr(browser_mod, "async_playwright", lambda: FakeAsyncPlaywright(page))

    escalator = PlaywrightEscalator()
    req = EscalationRequest(
        target_url="https://example.test/",
        user_agent="UA",
        viewport_width=800,
        viewport_height=600,
    )

    res: EscalationResult = await escalator._execute_playwright(req)
    assert res.resolved_successfully is True
    assert res.challenge_type_encountered in (ChallengeType.CONSENT_DIALOG, ChallengeType.NONE)
    assert "final" in res.rendered_html


@pytest.mark.asyncio
async def test_playwright_escalator_no_consent_branch(monkeypatch):
    html = "<div>no consent here</div>"
    page = FakePage(initial_html=html)
    import usurp.browser as browser_mod

    monkeypatch.setattr(browser_mod, "async_playwright", lambda: FakeAsyncPlaywright(page))

    escalator = PlaywrightEscalator()
    req = EscalationRequest(
        target_url="https://example.test/",
        user_agent="UA",
        viewport_width=800,
        viewport_height=600,
    )

    res = await escalator._execute_playwright(req)
    assert res.resolved_successfully is True
    assert res.challenge_type_encountered is ChallengeType.NONE
    assert "no consent" in res.rendered_html


@pytest.mark.asyncio
async def test_playwright_escalator_handles_missing_consent_buttons(monkeypatch):
    class NoButtonPage(FakePage):
        def get_by_role(self, role: str, name: str):
            class Button:
                @property
                def first(self):
                    return self

                async def click(self, timeout: int = 1000):
                    raise PlaywrightError("not found")

            return Button()

    page = NoButtonPage("Before you continue to Google")
    import usurp.browser as browser_mod

    monkeypatch.setattr(browser_mod, "async_playwright", lambda: FakeAsyncPlaywright(page))
    result = await PlaywrightEscalator().execute(
        EscalationRequest(
            target_url="https://example.test/",
            proxy_uri="http://proxy.example:8080",
            user_agent="UA",
            viewport_width=800,
            viewport_height=600,
        )
    )
    assert result.resolved_successfully is False


def test_playwright_proxy_server_rejects_missing_port() -> None:
    invalid = EscalationRequest.model_construct(
        target_url="https://example.test/",
        proxy_uri="http://proxy.example",
        user_agent="UA",
        viewport_width=800,
        viewport_height=600,
    )
    with pytest.raises(ValueError, match="host and port"):
        PlaywrightEscalator.proxy_server(invalid)

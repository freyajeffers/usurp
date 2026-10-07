import pytest

from usurp.browser import (
    ChallengeType,
    EscalationRequest,
    EscalationResult,
    PlaywrightEscalator,
)


@pytest.mark.asyncio
async def test_escalator_uses_injected_runner() -> None:
    request = EscalationRequest(
        target_url="https://www.google.com/search?q=test",
        user_agent="Mozilla/5.0",
        viewport_width=1280,
        viewport_height=900,
    )
    expected = EscalationResult(
        rendered_html="<html></html>",
        final_url="https://www.google.com/search?q=test",
        execution_duration_ms=10.0,
        challenge_type_encountered=ChallengeType.NONE,
        resolved_successfully=True,
    )

    async def runner(received: EscalationRequest) -> EscalationResult:
        assert received == request
        return expected

    result = await PlaywrightEscalator(runner=runner).execute(request)

    assert result == expected


def test_proxy_server_parser_handles_authless_proxy() -> None:
    request = EscalationRequest(
        target_url="https://example.test",
        proxy_uri="http://proxy.example.test:8080",
        user_agent="Mozilla/5.0",
        viewport_width=1280,
        viewport_height=900,
    )

    assert PlaywrightEscalator.proxy_server(request) == "http://proxy.example.test:8080"

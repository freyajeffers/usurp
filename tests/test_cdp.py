import pytest

from usurp.browser import ChallengeType, EscalationRequest, EscalationResult
from usurp.browser.cdp import CdpEscalator
from usurp.browser.chain import EscalationChain


def request() -> EscalationRequest:
    return EscalationRequest(
        target_url="https://example.test",
        user_agent="Mozilla/5.0",
        viewport_width=1280,
        viewport_height=900,
    )


def result(resolved: bool) -> EscalationResult:
    return EscalationResult(
        rendered_html="<html></html>",
        final_url="https://example.test",
        execution_duration_ms=1.0,
        challenge_type_encountered=ChallengeType.NONE,
        resolved_successfully=resolved,
    )


@pytest.mark.asyncio
async def test_escalation_chain_moves_to_cdp_after_camofox_failure() -> None:
    calls: list[str] = []

    async def camofox_runner(_: EscalationRequest) -> EscalationResult:
        calls.append("camofox")
        return result(False)

    async def cdp_runner(_: EscalationRequest) -> EscalationResult:
        calls.append("cdp")
        return result(True)

    response = await EscalationChain(
        (CdpEscalator(runner=camofox_runner), CdpEscalator(runner=cdp_runner))
    ).execute(request())

    assert response.resolved_successfully is True
    assert calls == ["camofox", "cdp"]


def test_cdp_without_endpoint_is_unresolved_not_an_exception() -> None:
    response = __import__("asyncio").run(CdpEscalator().execute(request()))
    assert response.resolved_successfully is False

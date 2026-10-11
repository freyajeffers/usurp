from unittest.mock import MagicMock, patch

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


@pytest.mark.asyncio
async def test_escalation_chain_continues_to_cdp_after_camofox_exception() -> None:
    calls: list[str] = []

    async def camofox_runner(_: EscalationRequest) -> EscalationResult:
        calls.append("camofox")
        raise RuntimeError("browser startup failed")

    async def cdp_runner(_: EscalationRequest) -> EscalationResult:
        calls.append("cdp")
        return result(True)

    response = await EscalationChain(
        (CdpEscalator(runner=camofox_runner), CdpEscalator(runner=cdp_runner))
    ).execute(request())

    assert response.resolved_successfully is True
    assert calls == ["camofox", "cdp"]


@pytest.mark.asyncio
async def test_escalation_chain_returns_unresolved_after_all_exceptions() -> None:
    async def failing(_: EscalationRequest) -> EscalationResult:
        raise RuntimeError("browser unavailable")

    response = await EscalationChain((CdpEscalator(runner=failing),)).execute(request())

    assert response.resolved_successfully is False
    assert response.challenge_type_encountered is ChallengeType.JS_CHALLENGE


def test_escalation_chain_requires_an_escalator() -> None:
    with pytest.raises(ValueError, match="at least one"):
        EscalationChain(())


@pytest.mark.asyncio
async def test_escalation_chain_asserts_if_internal_chain_is_cleared() -> None:
    chain = EscalationChain((CdpEscalator(),))
    chain._escalators = ()
    with pytest.raises(RuntimeError, match="no result"):
        await chain.execute(request())


@pytest.mark.asyncio
async def test_escalation_chain_returns_last_unresolved_result() -> None:
    async def unresolved(_: EscalationRequest) -> EscalationResult:
        return result(False)

    response = await EscalationChain((CdpEscalator(runner=unresolved),)).execute(request())
    assert response.resolved_successfully is False


def test_cdp_without_endpoint_is_unresolved_not_an_exception() -> None:
    with patch.object(CdpEscalator, "_detect_local_cdp_endpoint", return_value=None):
        response = __import__("asyncio").run(CdpEscalator().execute(request()))
    assert response.resolved_successfully is False


def test_cdp_auto_detects_default_local_endpoint() -> None:
    connection = MagicMock()
    with patch("usurp.browser.cdp.socket.create_connection", side_effect=[OSError, connection]):
        assert CdpEscalator._detect_local_cdp_endpoint() == "http://127.0.0.1:9223"
    connection.__enter__.assert_called_once()


def test_cdp_auto_detection_returns_none_when_ports_are_closed() -> None:
    with patch("usurp.browser.cdp.socket.create_connection", side_effect=OSError):
        assert CdpEscalator._detect_local_cdp_endpoint() is None


def test_cdp_proxy_server_preserves_scheme_host_and_port() -> None:
    cdp = CdpEscalator()
    assert cdp.proxy_server(request_with_proxy("http://proxy.example.test:8080")) == (
        "http://proxy.example.test:8080"
    )


def request_with_proxy(proxy_uri: str) -> EscalationRequest:
    return EscalationRequest(
        target_url="https://example.test",
        user_agent="Mozilla/5.0",
        viewport_width=1280,
        viewport_height=900,
        proxy_uri=proxy_uri,
    )


def test_cdp_proxy_server_rejects_proxy_without_port() -> None:
    with pytest.raises(ValueError, match="host and port"):
        CdpEscalator.proxy_server(request_with_proxy("http://proxy.example.test"))

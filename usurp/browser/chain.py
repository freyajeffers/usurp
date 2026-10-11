from __future__ import annotations

from collections.abc import Sequence
from time import monotonic
from typing import Protocol

from usurp.browser import ChallengeType, EscalationRequest, EscalationResult
from usurp.metrics import record_error, record_escalator_attempt


class Escalator(Protocol):
    async def execute(self, request: EscalationRequest) -> EscalationResult: ...


class EscalationChain:
    """Try browser escalators in order, stopping on success."""

    def __init__(self, escalators: Sequence[Escalator]) -> None:
        if not escalators:
            raise ValueError("escalation chain must contain at least one escalator")
        self._escalators = tuple(escalators)

    async def execute(self, request: EscalationRequest) -> EscalationResult:
        last_result: EscalationResult | None = None
        for escalator in self._escalators:
            name = escalator.__class__.__name__
            started = monotonic()
            try:
                result = await escalator.execute(request)
            except Exception as exc:  # noqa: BLE001 - continue to the next fallback
                record_error("escalator", type(exc).__name__)
                last_result = EscalationResult(
                    rendered_html="",
                    final_url=request.target_url,
                    execution_duration_ms=(monotonic() - started) * 1000,
                    challenge_type_encountered=ChallengeType.JS_CHALLENGE,
                    resolved_successfully=False,
                )
                record_escalator_attempt(name, last_result.execution_duration_ms / 1000)
                continue
            last_result = result
            record_escalator_attempt(name, (monotonic() - started))
            if last_result.resolved_successfully:
                return last_result
        if last_result is None:
            raise RuntimeError("escalation chain returned no result")
        return last_result


__all__ = ["EscalationChain", "Escalator"]

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from usurp.browser import EscalationRequest, EscalationResult
from usurp.metrics import ESCALATOR_ATTEMPTS


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
            ESCALATOR_ATTEMPTS.labels(escalator=escalator.__class__.__name__).inc()
            last_result = await escalator.execute(request)
            if last_result.resolved_successfully:
                return last_result
        assert last_result is not None
        return last_result


__all__ = ["EscalationChain", "Escalator"]

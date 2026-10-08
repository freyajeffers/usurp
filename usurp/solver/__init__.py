from __future__ import annotations

from typing import Protocol

from pydantic import HttpUrl, TypeAdapter

from usurp.browser import ChallengeType, EscalationRequest, EscalationResult


class SolverAdapter(Protocol):
    """Pluggable solver adapter interface.

    Implementations MAY perform human-assisted, third-party, or internal
    solving workflows. Integrators MUST ensure legal/compliance review before
    enabling any adapter. Adapters are NOT enabled by default; they must be
    explicitly wired into the SearchService and enabled via configuration.
    """

    async def solve(self, request: EscalationRequest) -> EscalationResult: ...


class MockSolverAdapter:
    """A non-production mock solver used for tests.

    It simply returns the provided challenge HTML as "rendered" with the
    same URL and reports resolved_successfully=False by default — tests can
    override behavior by subclassing or injecting a different mock.
    """

    def __init__(self, resolved: bool = False) -> None:
        self.resolved = resolved

    async def solve(self, request: EscalationRequest) -> EscalationResult:
        return EscalationResult(
            rendered_html=str(request.target_url),  # intentionally simple
            final_url=TypeAdapter(HttpUrl).validate_python(str(request.target_url)),
            execution_duration_ms=0.0,
            challenge_type_encountered=ChallengeType.NONE,
            resolved_successfully=self.resolved,
        )

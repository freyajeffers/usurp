import pytest

from usurp.browser import ChallengeType, EscalationRequest
from usurp.solver import MockSolverAdapter


@pytest.mark.asyncio
async def test_mock_solver_is_disabled_by_default() -> None:
    request = EscalationRequest(
        target_url="https://example.test",
        user_agent="Mozilla/5.0",
        viewport_width=1280,
        viewport_height=900,
    )

    result = await MockSolverAdapter().solve(request)

    assert result.resolved_successfully is False
    assert result.challenge_type_encountered is ChallengeType.NONE

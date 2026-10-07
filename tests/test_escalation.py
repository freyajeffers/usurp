from pathlib import Path

import pytest

from usurp.escalation import EscalationManager


def test_escalation_manager_persists_pending_ticket_and_validates_resolution(
    tmp_path: Path,
) -> None:
    manager = EscalationManager(tmp_path)
    ticket = manager.create_ticket("ticket-1", "example", "<html>captcha</html>")

    assert ticket["status"] == "pending"
    pending = manager.get_ticket("ticket-1")
    assert pending is not None
    assert pending["query"] == "example"

    result = manager.submit_solution(
        "ticket-1",
        '<div class="MjjYud"><a href="https://example.test"><h3>Result</h3></a></div>',
    )

    assert result["organic_results"][0]["title"] == "Result"
    resolved = manager.get_ticket("ticket-1")
    assert resolved is not None
    assert resolved["status"] == "resolved"


def test_escalation_manager_rejects_path_traversal_ticket_ids(tmp_path: Path) -> None:
    manager = EscalationManager(tmp_path)

    with pytest.raises(ValueError, match="ticket id"):
        manager.create_ticket("../outside", "query", "challenge")

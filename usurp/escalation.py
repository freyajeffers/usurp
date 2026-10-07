from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from usurp.parser import parse_serp_html


class EscalationManager:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path.home() / ".cache" / "usurp" / "escalations")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _ticket_path(self, ticket_id: str) -> Path:
        if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", ticket_id) is None:
            raise ValueError("ticket id must contain only letters, numbers, '_' or '-'")
        return self.base_dir / f"{ticket_id}.json"

    def create_ticket(
        self,
        ticket_id: str,
        query: str,
        challenge_html: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ticket = {
            "id": ticket_id,
            "query": query,
            "challenge_html": challenge_html,
            "metadata": metadata or {},
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._ticket_path(ticket_id).write_text(json.dumps(ticket, ensure_ascii=False))
        return ticket

    def list_tickets(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
            except OSError, json.JSONDecodeError:
                continue
            out.append(data)
        return out

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        path = self._ticket_path(ticket_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else None

    def submit_solution(self, ticket_id: str, rendered_html: str) -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            raise FileNotFoundError(ticket_id)
        response = parse_serp_html(rendered_html, query=ticket.get("query", ""))
        result_path = self.base_dir / f"{ticket_id}.result.json"
        result_path.write_text(json.dumps(response.model_dump(mode="json"), ensure_ascii=False))
        ticket["status"] = "resolved"
        ticket["resolved_at"] = datetime.now(UTC).isoformat()
        ticket["result_path"] = str(result_path)
        self._ticket_path(ticket_id).write_text(json.dumps(ticket, ensure_ascii=False))
        return response.model_dump(mode="json")

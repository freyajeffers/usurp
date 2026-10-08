#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from usurp.escalation import EscalationManager


def main() -> int:
    p = argparse.ArgumentParser(description="Submit rendered HTML to an escalation ticket")
    p.add_argument("ticket_id", help="Escalation ticket id")
    p.add_argument("html_file", type=Path, help="Rendered HTML file path")
    p.add_argument(
        "--escalations-dir",
        type=Path,
        default=Path.home() / ".cache" / "usurp" / "escalations",
        help="Local escalation storage directory (defaults to ~/.cache/usurp/escalations)",
    )
    args = p.parse_args()

    if not args.html_file.exists():
        print(f"error: html file not found: {args.html_file}", file=sys.stderr)
        return 2

    manager = EscalationManager(args.escalations_dir)
    ticket = manager.get_ticket(args.ticket_id)
    if ticket is None:
        print(f"error: ticket not found: {args.ticket_id}", file=sys.stderr)
        return 3
    try:
        manager.submit_solution(args.ticket_id, args.html_file.read_text())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4

    resolved = manager.get_ticket(args.ticket_id)
    print(
        "submitted, result saved to:",
        resolved.get("result_path", "<unknown>") if resolved else "<unknown>",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

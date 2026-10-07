import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from .models import ProxyNode


class ProxyPoolRouter:
    """Concurrency-safe proxy selection and cooldown tracking."""

    def __init__(self, nodes: list[ProxyNode], *, base_cooldown_seconds: float = 60.0) -> None:
        if base_cooldown_seconds <= 0:
            raise ValueError("base_cooldown_seconds must be positive")
        self._nodes = {node.id: node for node in nodes}
        self._sticky_sessions: dict[str, UUID] = {}
        self._base_cooldown_seconds = base_cooldown_seconds
        self._lock = asyncio.Lock()

    async def select(self, *, region: str, session_id: str | None = None) -> ProxyNode | None:
        async with self._lock:
            self._reactivate_expired()
            if session_id is not None:
                sticky_id = self._sticky_sessions.get(session_id)
                sticky_node = self._nodes.get(sticky_id) if sticky_id is not None else None
                if sticky_node is not None and self._available(sticky_node):
                    return sticky_node

            candidates = [
                node
                for node in self._nodes.values()
                if self._available(node) and node.region == region
            ]
            if not candidates:
                candidates = [node for node in self._nodes.values() if self._available(node)]
            if not candidates:
                return None

            selected = min(candidates, key=lambda node: (node.avg_latency_ms, str(node.id)))
            if session_id is not None:
                self._sticky_sessions[session_id] = selected.id
            return selected

    async def record_result(
        self, node_id: UUID, *, status_code: int, response_time_ms: float
    ) -> None:
        if response_time_ms < 0:
            raise ValueError("response_time_ms must be non-negative")
        async with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise KeyError(f"unknown proxy node: {node_id}")
            if status_code in {403, 429}:
                node.consecutive_failures += 1
                node.is_active = False
                cooldown = self._base_cooldown_seconds * (2 ** (node.consecutive_failures - 1))
                node.quarantined_until = datetime.now(UTC) + timedelta(seconds=cooldown)
                return

            if 200 <= status_code < 400:
                node.consecutive_failures = 0
                node.is_active = True
                node.quarantined_until = None
                node.avg_latency_ms = response_time_ms

    def _reactivate_expired(self) -> None:
        now = datetime.now(UTC)
        for node in self._nodes.values():
            if node.quarantined_until is not None and node.quarantined_until <= now:
                node.quarantined_until = None
                node.is_active = True

    @staticmethod
    def _available(node: ProxyNode) -> bool:
        return node.is_active and node.quarantined_until is None

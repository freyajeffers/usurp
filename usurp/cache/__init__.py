import asyncio
import hashlib
import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from usurp.parser import SerpApiResponse


class CacheSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ttl: timedelta = Field(default=timedelta(hours=24))

    @classmethod
    def validate_ttl(cls, value: timedelta) -> timedelta:
        if not timedelta(hours=1) <= value <= timedelta(days=30):
            raise ValueError("cache TTL must be between one hour and 30 days")
        return value


def canonical_parameters(parameters: dict[str, object]) -> str:
    normalized = {
        str(key).strip().lower(): str(value).strip().lower() for key, value in parameters.items()
    }
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def canonical_query_hash(parameters: dict[str, object]) -> str:
    return hashlib.sha256(canonical_parameters(parameters).encode()).hexdigest()


class SQLiteSerpCache:
    def __init__(self, path: Path, *, ttl: timedelta = timedelta(hours=24)) -> None:
        if not timedelta(hours=1) <= ttl <= timedelta(days=30):
            raise ValueError("cache TTL must be between one hour and 30 days")
        self._path = path
        self._ttl_ms = int(ttl.total_seconds() * 1000)
        self._write_lock = asyncio.Lock()

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    async def set(self, parameters: dict[str, object], response: SerpApiResponse) -> None:
        await self.initialize()
        now = int(time.time() * 1000)
        query_hash = canonical_query_hash(parameters)
        payload = response.model_dump_json()
        async with self._write_lock:
            await asyncio.to_thread(
                self._set_sync,
                query_hash,
                str(parameters.get("q", "")),
                canonical_parameters(parameters),
                payload,
                now,
                now + self._ttl_ms,
            )

    async def get(self, parameters: dict[str, object]) -> SerpApiResponse | None:
        await self.initialize()
        row = await asyncio.to_thread(self._get_sync, canonical_query_hash(parameters))
        if row is None:
            return None
        return SerpApiResponse.model_validate_json(row)

    async def pragmas(self) -> dict[str, Any]:
        await self.initialize()
        return await asyncio.to_thread(self._pragmas_sync)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA mmap_size = 268435456")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        except BaseException:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def _initialize_sync(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS serp_cache (
                    query_hash TEXT PRIMARY KEY,
                    raw_query TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 1
                )""")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_serp_cache_expires ON serp_cache(expires_at)"
            )

    def _set_sync(self, *values: object) -> None:
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO serp_cache
                (query_hash, raw_query, parameters_json, response_json, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(query_hash) DO UPDATE SET
                    response_json=excluded.response_json,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at,
                    hit_count=serp_cache.hit_count + 1""",
                values,
            )

    def _get_sync(self, query_hash: str) -> str | None:
        now = int(time.time() * 1000)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT response_json FROM serp_cache WHERE query_hash = ? AND expires_at > ?",
                (query_hash, now),
            ).fetchone()
            if row is None:
                connection.execute("DELETE FROM serp_cache WHERE query_hash = ?", (query_hash,))
                return None
            connection.execute(
                "UPDATE serp_cache SET hit_count = hit_count + 1 WHERE query_hash = ?",
                (query_hash,),
            )
            return str(row[0])

    def _pragmas_sync(self) -> dict[str, Any]:
        with self._connection() as connection:
            return {
                "journal_mode": str(connection.execute("PRAGMA journal_mode").fetchone()[0]),
                "synchronous": int(connection.execute("PRAGMA synchronous").fetchone()[0]),
                "busy_timeout": int(connection.execute("PRAGMA busy_timeout").fetchone()[0]),
                "mmap_size": int(connection.execute("PRAGMA mmap_size").fetchone()[0]),
            }


__all__ = ["SQLiteSerpCache", "canonical_parameters", "canonical_query_hash"]

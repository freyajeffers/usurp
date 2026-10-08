import sqlite3
from datetime import timedelta

import pytest

from usurp.cache import SQLiteSerpCache, canonical_query_hash
from usurp.parser import parse_serp_html


@pytest.mark.asyncio
async def test_cache_canonicalizes_parameter_order_and_case(tmp_path) -> None:
    first = {"q": "  Quantum Error Correction ", "gl": "US", "hl": "en"}
    second = {"hl": "en", "gl": "us", "q": "quantum error correction"}
    assert canonical_query_hash(first) == canonical_query_hash(second)

    cache = SQLiteSerpCache(tmp_path / "cache.db", ttl=timedelta(hours=1))
    response = parse_serp_html("<div id='search'></div>", query="test")
    await cache.set(first, response)

    cached = await cache.get(second)
    assert cached is not None
    assert cached.search_parameters.q == "test"


@pytest.mark.asyncio
async def test_cache_expires_entries(tmp_path) -> None:
    cache = SQLiteSerpCache(tmp_path / "cache.db")
    response = parse_serp_html("<div id='search'></div>", query="test")
    params = {"q": "test"}
    await cache.set(params, response)

    connection = sqlite3.connect(tmp_path / "cache.db")
    try:
        connection.execute("UPDATE serp_cache SET expires_at = 0")
        connection.commit()
    finally:
        connection.close()

    assert await cache.get(params) is None


@pytest.mark.asyncio
async def test_cache_uses_required_wal_pragmas(tmp_path) -> None:
    cache = SQLiteSerpCache(tmp_path / "cache.db")
    await cache.initialize()
    pragmas = await cache.pragmas()
    assert pragmas == {
        "journal_mode": "wal",
        "synchronous": 1,
        "busy_timeout": 5000,
        "mmap_size": 268435456,
    }

from __future__ import annotations

import pytest

from usurp.metrics import (
    CACHE_HITS,
    CACHE_MISSES,
    CDP_AVAILABLE,
    ERRORS,
    INFLIGHT_REQUESTS,
    LAST_SUCCESS_TIMESTAMP,
    RESULTS_COUNT,
    SEARCH_COUNTER,
    SEARCH_LATENCY,
    TRANSPORT_ATTEMPTS,
    TRANSPORT_LATENCY,
    mark_cdp_available,
    metrics_response,
    record_cache_hit,
    record_cache_miss,
    record_error,
    record_escalator_attempt,
    record_search,
    record_transport_attempt,
    track_inflight,
)


def test_metrics_helpers_record_values() -> None:
    mark_cdp_available(True)
    assert CDP_AVAILABLE._value.get() == 1.0
    mark_cdp_available(False)
    assert CDP_AVAILABLE._value.get() == 0.0

    record_cache_hit(12.5)
    record_cache_hit(None)
    record_cache_miss()
    record_search(0.25, results_count=3, request_bytes=20, response_bytes=80)
    record_transport_attempt("fastpath", True, latency_seconds=0.1)
    record_transport_attempt("browser", False)
    record_escalator_attempt("Camoufox", latency_seconds=0.2)
    record_escalator_attempt("CDP")
    record_error("transport", "timeout")

    assert CACHE_HITS._value.get() >= 2.0
    assert CACHE_MISSES._value.get() >= 1.0
    assert SEARCH_COUNTER._value.get() >= 1.0
    assert SEARCH_LATENCY._sum.get() >= 0.25
    assert RESULTS_COUNT._sum.get() >= 3.0
    assert TRANSPORT_ATTEMPTS.labels("fastpath", "success")._value.get() >= 1.0
    assert TRANSPORT_ATTEMPTS.labels("browser", "failure")._value.get() >= 1.0
    assert TRANSPORT_LATENCY.labels("fastpath")._sum.get() >= 0.1
    assert ERRORS.labels("transport", "timeout")._value.get() >= 1.0
    assert LAST_SUCCESS_TIMESTAMP._value.get() > 0


def test_metrics_response_and_inflight_cleanup() -> None:
    body, content_type = metrics_response()
    assert b"usurp_cache_hits_total" in body
    assert content_type
    assert INFLIGHT_REQUESTS._value.get() == 0.0

    with track_inflight():
        assert INFLIGHT_REQUESTS._value.get() == 1.0
    assert INFLIGHT_REQUESTS._value.get() == 0.0

    with pytest.raises(RuntimeError), track_inflight():
        raise RuntimeError("cleanup")
    assert INFLIGHT_REQUESTS._value.get() == 0.0

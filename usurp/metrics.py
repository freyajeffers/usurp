from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from time import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

# Basic request counters & latency
SEARCH_COUNTER = Counter(
    "usurp_search_requests_total",
    "Total number of search requests",
    registry=REGISTRY,
)
SEARCH_LATENCY = Histogram(
    "usurp_search_latency_seconds",
    "Search request latency in seconds",
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10),
    registry=REGISTRY,
)

# Transport-specific metrics
TRANSPORT_ATTEMPTS = Counter(
    "usurp_transport_attempts_total",
    "Total number of transport attempts",
    ["transport_name", "outcome"],  # outcome: success|failure
    registry=REGISTRY,
)
TRANSPORT_LATENCY = Histogram(
    "usurp_transport_latency_seconds",
    "Transport request latency by transport",
    ["transport_name"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10),
    registry=REGISTRY,
)

# Cache metrics
CACHE_HITS = Counter("usurp_cache_hits_total", "Number of cache hits", registry=REGISTRY)
CACHE_MISSES = Counter("usurp_cache_misses_total", "Number of cache misses", registry=REGISTRY)
CACHE_TTL_HIST = Histogram(
    "usurp_cache_ttl_seconds", "TTL observed on cached entries", registry=REGISTRY
)

# Escalator metrics
ESCALATOR_ATTEMPTS = Counter(
    "usurp_escalator_attempts_total",
    "Total number of escalator invocation attempts",
    ["escalator"],
    registry=REGISTRY,
)
ESCALATOR_LATENCY = Histogram(
    "usurp_escalator_latency_seconds",
    "Latency per escalator invocation",
    ["escalator"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10, 30),
    registry=REGISTRY,
)

# Parser / result metrics
RESULTS_COUNT = Histogram(
    "usurp_search_results_count",
    "Number of results returned by a search",
    buckets=(0, 1, 3, 5, 10, 20, 50, 100),
    registry=REGISTRY,
)

# Runtime gauges
INFLIGHT_REQUESTS = Gauge(
    "usurp_inflight_requests", "Currently in-flight search requests", registry=REGISTRY
)
CDP_AVAILABLE = Gauge(
    "usurp_cdp_available",
    "Whether a configured CDP endpoint is enabled (1 = configured, 0 = disabled)",
    registry=REGISTRY,
)
LAST_SUCCESS_TIMESTAMP = Gauge(
    "usurp_last_success_timestamp",
    "Unix timestamp of the last successful search",
    registry=REGISTRY,
)

# Error tracking
ERRORS = Counter(
    "usurp_errors_total",
    "Count of error events",
    ["component", "type"],
    registry=REGISTRY,
)

# Size metrics
REQUEST_SIZE = Histogram(
    "usurp_request_size_bytes",
    "Approximate request size in bytes",
    registry=REGISTRY,
)
RESPONSE_SIZE = Histogram(
    "usurp_response_size_bytes",
    "Approximate response size in bytes",
    registry=REGISTRY,
)


def metrics_response() -> tuple[bytes, str]:
    """Return the prometheus metrics response body and content type."""

    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


# Convenience helpers used across the codebase
def mark_cdp_available(enabled: bool) -> None:
    CDP_AVAILABLE.set(1.0 if enabled else 0.0)


def record_cache_hit(ttl_seconds: float | None) -> None:
    CACHE_HITS.inc()
    if ttl_seconds is not None:
        CACHE_TTL_HIST.observe(ttl_seconds)


def record_cache_miss() -> None:
    CACHE_MISSES.inc()


def record_search(
    latency_seconds: float,
    transport: str = "fastpath",
    results_count: int | None = None,
    request_bytes: int | None = None,
    response_bytes: int | None = None,
) -> None:
    """Record a completed search request with optional auxiliary metrics."""
    SEARCH_COUNTER.inc()
    SEARCH_LATENCY.observe(latency_seconds)
    record_transport_attempt(transport, True, latency_seconds)
    if results_count is not None:
        RESULTS_COUNT.observe(results_count)
    if request_bytes is not None:
        REQUEST_SIZE.observe(request_bytes)
    if response_bytes is not None:
        RESPONSE_SIZE.observe(response_bytes)
    LAST_SUCCESS_TIMESTAMP.set(time())


def record_transport_attempt(
    transport_name: str, success: bool, latency_seconds: float | None = None
) -> None:
    TRANSPORT_ATTEMPTS.labels(
        transport_name=transport_name, outcome=("success" if success else "failure")
    ).inc()
    if latency_seconds is not None:
        TRANSPORT_LATENCY.labels(transport_name=transport_name).observe(latency_seconds)


def record_escalator_attempt(escalator: str, latency_seconds: float | None = None) -> None:
    ESCALATOR_ATTEMPTS.labels(escalator=escalator).inc()
    if latency_seconds is not None:
        ESCALATOR_LATENCY.labels(escalator=escalator).observe(latency_seconds)


def record_error(component: str, err_type: str = "exception") -> None:
    ERRORS.labels(component=component, type=err_type).inc()


@contextmanager
def track_inflight() -> Iterator[None]:
    """Context manager to increment/decrement the in-flight requests gauge.

    Usage:
        with track_inflight():
            ...
    """
    INFLIGHT_REQUESTS.inc()
    try:
        yield
    finally:
        INFLIGHT_REQUESTS.dec()

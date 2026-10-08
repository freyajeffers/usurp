from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

SEARCH_COUNTER = Counter(
    "usurp_search_requests_total",
    "Total number of search requests",
    registry=REGISTRY,
)
SEARCH_LATENCY = Histogram(
    "usurp_search_latency_seconds",
    "Search request latency in seconds",
    registry=REGISTRY,
)
ESCALATOR_ATTEMPTS = Counter(
    "usurp_escalator_attempts_total",
    "Total number of escalator invocation attempts",
    ["escalator"],
    registry=REGISTRY,
)
CDP_AVAILABLE = Gauge(
    "usurp_cdp_available",
    "Whether a configured CDP endpoint is enabled (1 = configured, 0 = disabled)",
    registry=REGISTRY,
)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST

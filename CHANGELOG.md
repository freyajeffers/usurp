# Changelog

All notable changes to usurp are documented here.

## Unreleased

- Added the initial `uv` Python package scaffold.
- Added strict Phase 1 transport contracts for proxy nodes, requests, and results.
- Added a minimal `/search` ASGI endpoint returning the SerpApi-compatible root keys used by the scaffold.
- Added pytest coverage and the repository quality-gate configuration.
- Switched the project to Python 3.14.8 via `.python-version` and `requires-python`.
- Upgraded and re-locked runtime and development dependencies with `uv lock --upgrade`.
- Updated installation documentation to use `uv sync --extra dev`.
- Added the first Phase 1 fast-path transport client using curl-cffi browser impersonation.
- Added request parameter construction, configurable connect/read timeouts, proxy forwarding, response timing, and anti-bot escalation markers.
- Added a concurrency-safe proxy pool with regional selection, sticky sessions, exponential cooldowns, failover, and latency tracking.
- Added desktop/mobile user-agent routing and consent-cookie injection to the fast path.
- Added strict Phase 2 escalation contracts and challenge classification for consent, JavaScript, and hard CAPTCHA interstitials.

Not implemented yet: browser fallback, SERP parsing, caching, authentication, and systemd packaging.

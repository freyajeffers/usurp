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

Not implemented yet: live transport, proxy routing, browser fallback, SERP parsing, caching, authentication, and systemd packaging.

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
- Added the initial selectolax-based SERP parser and strict SerpApi response models for organic results and search metadata.
- Added asynchronous SQLite WAL caching with canonical SHA-256 query keys, TTL expiry, hit counts, and required concurrency pragmas.
- Added token-bucket rate limiting with per-key burst capacity, refill, proxy delay enforcement, and reset support.
- Added `SearchService` orchestration for transport, challenge escalation, parsing, and optional cache hits.
- Replaced the placeholder API with `/search`, `/v1/search`, and `/health` endpoints backed by dependency-injected search services.
- Added optional constant-time API-key enforcement through `USURP_API_KEY`.
- Added bounded Playwright browser escalation execution with proxy support, viewport/user-agent settings, consent-button handling, cleanup, and challenge result reporting.
- Integrated browser escalation into `SearchService` and the default FastAPI service dependency.
- Wired token-bucket rate limiting into `SearchService` and the REST API with per-client keys and HTTP 429 responses.
- Expanded SERP parsing for knowledge graphs, related questions, related searches, and next-page pagination.
- Added a hardened systemd user-service unit and deployment instructions under `packaging/systemd/`.
- Added static SERP fixture coverage for organic, featured-snippet, knowledge-panel, mobile, and pagination layouts.
- Expanded the static fixture corpus to 50 representative layouts and added an all-fixture extraction regression test.
- Added detection for Google's `/httpservice/retry/enablejs` interstitial observed during live fast-path validation.
- Added typed fail-closed browser challenge errors and structured HTTP 503 responses for unresolved CAPTCHA/challenge states.
- Added local escalation tickets for authorized human-in-the-loop review and rendered-HTML submission without automated CAPTCHA bypass.
- Added Camoufox as the primary browser escalator with Playwright fallback; Camoufox remains render-only and does not solve CAPTCHAs.
- Added a disabled-by-default `SolverAdapter` protocol with a non-solving mock adapter for approved human/internal integrations.
- Added an opt-in official Google Programmable Search fallback using `USURP_GOOGLE_CSE_API_KEY` and `USURP_GOOGLE_CSE_ID`; credentials are never logged.
- Camoufox humanization, sticky proxy routing, cooldowns, and fail-closed challenge handling remain enabled as challenge-avoidance measures.
- Verified Camoufox ARM64 browser installation and live rendering against `example.com`; Google challenge responses remain fail-closed.
- Added authenticated escalation-admin endpoints to list pending tickets and submit human-reviewed rendered HTML.
- Added a minimal authenticated browser UI at `/admin/ui` for listing tickets and uploading reviewed HTML.
- Added an optional Chromium DevTools Protocol escalation stage between Camoufox and human-review tickets, enabled with `USURP_CDP_ENDPOINT`.
- Added Prometheus instrumentation and an authenticated-independent `/metrics` endpoint for search latency, request volume, and escalator attempts.
- Added an ARM-friendly Dockerfile and GitHub Actions CI for lint, tests, and multi-architecture image builds.
- Expanded test coverage with marked HTTP integration tests for transport → escalation → parser → cache and unresolved-ticket flows; CI now runs unit coverage (minimum 80%), integration tests, and mypy.
- Expanded unit and backend fakes to exercise every application branch; CI now enforces 100% statement coverage.
- Hardened escalation ticket IDs against path traversal and unsafe filesystem names.

Not implemented yet: production validation against captured real Google layouts.

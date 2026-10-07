# Master Phased Implementation Plan: usurp (Autonomous Google SERP Extraction Engine)

---

Autonomous Google SERP Extraction Engine (usurp) — Architectural
Delivery Roadmap

## 1. Executive Overview & Phase Sequencing

---

This Master Implementation Plan details the phased construction of the
Autonomous Google SERP Extraction Engine (usurp). Engineered as a
high-throughput, privacy-sovereign microservice, usurp provides a
drop-in 1:1 replacement for SerpApi's Google Search capabilities without
recurrent per-search billing fees or external logging.

The project is organized into five strictly ordered, dependency-gated
phases. Each phase establishes clear architectural boundaries, typed
Pydantic v2 data contracts, automated unit and integration tests, and
explicit verification gates before subsequent milestones can be
unlocked.

## 2. Cross-Phase Dependency Graph

---

┌────────────────────────────────────────────────────────┐\
│ Phase 1: Request Transport, TLS & Proxy Orchestration  │\
└───────────────────────────┬────────────────────────────┘\
                           │ (Outputs Raw HTML via Fast-Path TLS
Transport)\
                           ▼\
┌────────────────────────────────────────────────────────┐\
│ Phase 2: Stealth Browser Fallback & Bot Escalation     │\
└───────────────────────────┬────────────────────────────┘\
                           │ (Outputs Rendered DOM on Challenged
Requests)\
                           ▼\
┌────────────────────────────────────────────────────────┐\
│ Phase 3: Resilient DOM Parser & SerpApi Normalizer     │\
└───────────────────────────┬────────────────────────────┘\
                           │ (Outputs Standardized SerpApi JSON
Objects)\
                           ▼\
┌────────────────────────────────────────────────────────┐\
│ Phase 4: Local Caching, Concurrency & Rate Limiting    │\
└───────────────────────────┬────────────────────────────┘\
                           │ (Outputs Non-Blocking Cached Search
Pipeline)\
                           ▼\
┌────────────────────────────────────────────────────────┐\
│ Phase 5: REST API, Client Layer & Systemd Sandboxing   │\
└────────────────────────────────────────────────────────┘\
 (Outputs Production Drop-in API & Hardened Background Daemon)

## 3. Phase Summaries & Deliverables Table

---

Phase

Core Focus

Primary Deliverables

Blocking Exit Gate

 

Phase 1

Request Transport, TLS & Proxy Pool

- Asynchronous curl_cffi HTTP client with browser TLS impersonation.
- Proxy pool router with cooldown, latency tracking, and gl geo-routing.
- Mobile WAP/WebKit fast-path routing and consent cookie generator.

\>98% connection success rate on clean proxy pools; TLS fingerprint
verified as legitimate Chrome/Safari; transport latency \<450ms.

Phase 2

Stealth Browser Fallback & Bot Escalation

- Playwright / Camoufox stealth browser execution pool.
- Circuit breaker & escalation controller detecting HTTP
  429/503/CAPTCHA.
- Automated consent banner handler (Google "Before you continue"
  interstitial).
- WebGL, Canvas, AudioContext, and Navigator stealth patches.

100% automated recovery on consent challenge fixtures; zero browser
resource leakage; fallback execution \<1.8s.

Phase 3

Resilient DOM Parser & SerpApi Normalizer

- Selectolax/lxml semantic tree extraction engine.
- Extractors for Organic Results, Featured Snippets, Knowledge Graph,
  PAA, and Pagination.
- Pydantic v2 data models normalizing output to exact SerpApi JSON
  schema.

≥96% field extraction accuracy across 100 historical SERP HTML test
fixtures; 100% schema validation against SerpApi benchmark.

Phase 4

Local Caching, Concurrency & Rate Limiting

- SQLite WAL mode SERP cache with SHA-256 query hashing.
- Configurable TTL management (default 24h) and no_cache overrides.
- Token-bucket rate limiter per domain and proxy node.
- Asynchronous worker task queue with bounded concurrency.

100% cache hit verification on identical query parameters; zero SQLite
locking errors under 100 concurrent reads/writes; lookup \<5ms.

Phase 5

REST API, Client Layer & Systemd Sandboxing

- FastAPI endpoints: GET /search, POST /v1/search, GET /health.
- Constant-time token authentication middleware.
- Full compatibility testing with official google-search-results Python
  SDK.
- Linux systemd user service unit with strict sandboxing and journald
  logging.

Official SerpApi client library executes test suite seamlessly against
usurp; zero systemd permission violations; API latency SLA met.

## 4. Cross-Phase Interaction Contracts

---

- Transport to Escalation Boundary: Phase 1 emits a TransportResult
  containing raw HTML, status code, and anti-bot signals. If status
  indicates a CAPTCHA or blocking interstitial, the escalation
  controller in Phase 2 initiates browser rendering without bubbling an
  error to client code.
- Parser to Caching Boundary: Phase 3 parses HTML into a typed
  SerpApiResponse object. Phase 4 captures this structured response
  alongside the SHA-256 parameter signature, persisting the serialized
  JSON payload into SQLite with timestamp and expiration metadata.
- Cache to REST Gateway Boundary: Inbound requests in Phase 5 query
  Phase 4 cache before invoking Phase 1 transport. If a valid, unexpired
  cache record exists and no_cache is false, the cached payload is
  returned instantly in sub-5ms latency.

## 5. Operational Invariants & Definition of Done

- Invariant 1: Exact SerpApi Output Compatibility: The JSON output
  produced for any search query must conform strictly to SerpApi's field
  naming and structure (e.g., search_metadata, search_parameters,
  organic_results containing position, title, link, snippet), ensuring
  client code requires zero modification.
- Invariant 3: Multi-Tiered Transport Fast-Path: Always attempt
  high-speed HTTP/2 TLS fast-path requests first; escalate to headless
  stealth browser pools only upon receiving explicit anti-bot challenge
  markers.
-
- Invariant 5: Resource Boundedness & Process Recycling: Headless
  browser pools must never exceed the configured concurrency ceiling
  (default: 4 instances), and browser contexts must be recycled after 25
  operations to guarantee zero memory leakage.
- Invariant 7: Explicit Public API Surface: All internal modules and
  implementation details must remain private by default. Every
  public-facing package must use \_\_init\_\_.py to export its primary
  interfaces via \_\_all\_\_, enabling a flat and stable developer API.
  Deep imports into implementation sub-modules are strictly prohibited
  for consumers.
- Invariant 8: Pydantic-First Data Contracts: Use Pydantic v2 BaseModel
  schemas for every input, output, configuration, cache, and
  inter-module data contract wherever technically possible. Enable
  strict validation, reject unknown fields, validate assignments where
  state is mutable, and use field/model validators for invariants. Use
  dataclasses only when a Pydantic model cannot represent the
  requirement and document that exception.
- Invariant 9: Mature Library Reuse: Prefer the Python standard library
  and already-declared, maintained external libraries over custom
  implementations of established functionality. Before adding bespoke
  parsing, validation, serialization, HTTP, retry, rate-limiting,
  statistics, or concurrency code, check whether an appropriate standard
  or project dependency provides it. Add a dependency only when it
  materially improves correctness or security, then lock and test it.
- Invariant 10: Tests Before Implementation: For every new behavior,
  boundary, bug fix, and phase component, write exhaustive unit and
  contract tests first. Run the new tests to establish the failing or
  missing behavior, implement only what they require, then run the full
  quality gate before committing. Include valid, invalid, boundary,
  failure, serialization, and integration-path cases where applicable.
- Invariant 11: Full Boundary Validation: Validate every public input
  before processing and every public output before returning or
  persisting it. Validation must cover types, structure, required
  fields, ranges, lengths, encodings, paths, URLs, enums, offsets,
  hashes, serialized payloads, provider responses, and error states.
  Fail closed with typed validation errors; never silently coerce
  malformed or incomplete data.
- Invariant 12: Tooling Quality Gates: All commits touching source code
  must pass the project's static and test gates locally before pushing:
  uv run ruff check . --fix (or uv run ruff check .), uv run black
  --check ., uv run mypy usurp, and uv run pytest -q. CI must run the
  same commands on PRs and block merges until they pass. Document any
  allowed exceptions in CONTRIBUTING.md and record approvals in PR
  descriptions.
- Invariant 13: Atomic Commits and Just-in-Time Documentation: Maintain
  an atomic commit history by grouping logically related
  changes—including source code, tests, and documentation—into single,
  cohesive commits. Document new modules, configurations, and public
  APIs as they are implemented, ensuring that docs/ and AGENTS.md
  reflect the current state of the repository. Never batch unrelated
  features or fixes into a single commit; never commit code without
  accompanying test and documentation updates.
- Invariant 14: README and Changelog Currency: Keep README.md accurate
  for the current checkout: supported functionality, setup, exact
  commands, public APIs, and known limitations. Keep root CHANGELOG.md
  updated with each user-visible or developer-relevant change, grouped
  by release or unreleased work. Never document planned or specified
  functionality as implemented.
- Invariant 15: Documentation Currency: Keep all project documentation
  synchronized with the implementation, tests, configuration, and
  invariant audit. Update the relevant README, changelog, development
  guide, runbook, technical specification, or audit document in the same
  logically grouped change as the code it describes. Remove stale
  commands, claims, and examples rather than preserving them for
  historical context.
- Invariant 16: Tests Before Code Updates: When an existing behavior or
  contract must change, update or add the affected tests first, run them
  to demonstrate the expected failure or gap, then update the
  implementation. Do not change production code first and retrofit tests
  afterward; include regression coverage for every changed
  behavior.Invariant 4: Non-Blocking SQLite Concurrency: All SQLite
  connections must be configured with Write-Ahead Logging (PRAGMA
  journal_mode = WAL;), PRAGMA busy_timeout = 5000;, PRAGMA synchronous
  = NORMAL;, and PRAGMA mmap_size = 268435456;. Never hold write
  transactions open across network I/O or model inference calls.

# AGENTS.md: Developer & Coding Agent Guidelines — usurp

---

Autonomous Google SERP Extraction Engine (usurp) — Operational
Invariants & Rules

## 1. Agent Persona & Mission Statement

---

You are an autonomous systems engineering agent responsible for
developing, maintaining, and hardening the Autonomous Google SERP
Extraction Engine (usurp). Your mission is to build a reliable,
high-performance, private search extraction service that functions as a
seamless, 1:1 drop-in replacement for SerpApi.

You prioritize correctness, local data sovereignty, defensive
concurrency, strict Pydantic typing, non-blocking I/O, and disciplined
resource consumption over hasty implementations or monolithic code
bloat.

## 2. Core Operational Invariants (Non-Negotiable)

- Invariant 1: Exact SerpApi Output Compatibility\
  The REST output returned by usurp must adhere 100% to SerpApi's
  standard JSON schema structure. Field names like organic_results,
  position, title, link, snippet, knowledge_graph, and pagination must
  match verbatim. Never introduce idiosyncratic root keys that break
  upstream SDK integrations (e.g. LangChain, LlamaIndex).
- Invariant 3: Multi-Tiered Transport Discipline\
  Always attempt high-speed HTTP/2 TLS fast-path requests (via
  curl_cffi) first. Do not invoke heavy headless browser instances
  unless the fast-path triggers an explicit anti-bot challenge or
  CAPTCHA interstitial.
- Invariant 4: Non-Blocking SQLite Concurrency\
  All SQLite connections must be configured with Write-Ahead Logging
  (PRAGMA journal_mode = WAL;), PRAGMA busy_timeout = 5000;, PRAGMA
  synchronous = NORMAL;, and PRAGMA mmap_size = 268435456;. Never hold
  write transactions open across network I/O or model inference calls.
- Invariant 5: Resource Boundedness\
  Headless browser pools must never exceed the configured concurrency
  ceiling (default: 4 instances). Every browser context must be recycled
  after 25 operations or upon encountering an unhandled error to prevent
  memory leaks.
- Invariant 7: Explicit Public API Surface\
  All internal modules and implementation details must remain private by
  default. Every public-facing package must use \_\_init\_\_.py to
  export its primary interfaces via \_\_all\_\_, enabling a flat and
  stable developer API. Deep imports into implementation sub-modules are
  strictly prohibited for consumers.
- Invariant 8: Pydantic-First Data Contracts\
  Use Pydantic v2 BaseModel schemas for every input, output,
  configuration, cache, and inter-module data contract wherever
  technically possible. Enable strict validation, reject unknown fields,
  validate assignments where state is mutable, and use field/model
  validators for invariants. Use dataclasses only when a Pydantic model
  cannot represent the requirement and document that exception.
- Invariant 9: Mature Library Reuse\
  Prefer the Python standard library and already-declared, maintained
  external libraries over custom implementations of established
  functionality. Before adding bespoke parsing, validation,
  serialization, HTTP, retry, rate-limiting, statistics, or concurrency
  code, check whether an appropriate standard or project dependency
  provides it. Add a dependency only when it materially improves
  correctness or security, then lock and test it.
- Invariant 10: Tests Before Implementation\
  For every new behavior, boundary, bug fix, and phase component, write
  exhaustive unit and contract tests first. Run the new tests to
  establish the failing or missing behavior, implement only what they
  require, then run the full quality gate before committing. Include
  valid, invalid, boundary, failure, serialization, and integration-path
  cases where applicable.
- Invariant 11: Full Boundary Validation\
  Validate every public input before processing and every public output
  before returning or persisting it. Validation must cover types,
  structure, required fields, ranges, lengths, encodings, paths, URLs,
  enums, offsets, hashes, serialized payloads, provider responses, and
  error states. Fail closed with typed validation errors; never silently
  coerce malformed or incomplete data.
- Invariant 12: Tooling Quality Gates\
  All commits touching source code must pass the project's static and
  test gates locally before pushing: uv run ruff check . --fix (or uv
  run ruff check .), uv run black --check ., uv run mypy usurp, and uv
  run pytest -q. CI must run the same commands on PRs and block merges
  until they pass. Document any allowed exceptions in CONTRIBUTING.md
  and record approvals in PR descriptions.
- Invariant 13: Atomic Commits and Just-in-Time Documentation\
  Maintain an atomic commit history by grouping logically related
  changes—including source code, tests, and documentation—into single,
  cohesive commits. Document new modules, configurations, and public
  APIs as they are implemented, ensuring that docs/ and AGENTS.md
  reflect the current state of the repository. Never batch unrelated
  features or fixes into a single commit; never commit code without
  accompanying test and documentation updates.
- Invariant 14: README and Changelog Currency\
  Keep README.md accurate for the current checkout: supported
  functionality, setup, exact commands, public APIs, and known
  limitations. Keep root CHANGELOG.md updated with each user-visible or
  developer-relevant change, grouped by release or unreleased work.
  Never document planned or specified functionality as implemented.
- Invariant 15: Documentation Currency\
  Keep all project documentation synchronized with the implementation,
  tests, configuration, and invariant audit. Update the relevant README,
  changelog, development guide, runbook, technical specification, or
  audit document in the same logically grouped change as the code it
  describes. Remove stale commands, claims, and examples rather than
  preserving them for historical context.
- Invariant 16: Tests Before Code Updates\
  When an existing behavior or contract must change, update or add the
  affected tests first, run them to demonstrate the expected failure or
  gap, then update the implementation. Do not change production code
  first and retrofit tests afterward; include regression coverage for
  every changed behavior.

## 3. Engineering Discipline & Prohibitions

---

- No Code Bloat or Premature Monoliths: Avoid gigantic files. Keep
  modules focused, single-purpose, and under 300 lines of code (e.g.,
  transport/, browser/, parsers/, cache/, api/).
- Strict Typing: Enforce Python 3.11+ type annotations across 100% of
  function signatures. Use Pydantic v2 schemas for all inter-subsystem
  data contracts.
- Clean Terminal & Editor Hygiene: Ensure .gitignore and packaging rules
  proactively filter transient editor artifacts (Vim swap files .\*.swp,
  persistent undo files .\*.un~, backup files \*~, and temporary writes
  \*.tmp).
- Hardware-Aware Concurrency: Pin intra-op thread pools to physical core
  counts and restrict inter-op threads to 1 when local ML/embedding
  models are employed. Use asyncio for all network I/O.
- Constant-Time Security Comparisons: When verifying API tokens or
  authorization headers, always use secrets.compare_digest() to
  eliminate timing side-channel attacks.

## 4. Test-Driven Development (TDD) Protocols & Quality Gates

---

- TDD First & Test Driven Protocols (Invariants 10 & 16): Write unit and
  contract tests before implementing features or updating behaviors.
  Always execute tests first to verify expected failures before writing
  or changing production code.
- Fixture-Based Parser Testing: Maintain a corpus of at least 50 static
  Google SERP HTML files representing diverse query types (organic only,
  featured snippets, knowledge panels, local maps, multi-column search,
  mobile WAP). All parser modifications must pass 100% of regression
  fixtures.
- Tooling Quality Gates (Invariant 12): All commits must pass static
  checks and test suites locally before pushing using: uv run ruff check
  . --fix, uv run black --check ., uv run mypy usurp, and uv run pytest
  -q.
- Coverage Standards:

<!-- -->

- Unit test coverage ≥ 90% across core parsing and caching logic.
- End-to-end integration tests covering proxy failover and challenge
  escalation.
- Drop-in validation tests using the official google-search-results
  Python library.

## 5. Component Latency Budgets & Performance SLAs

---

Operation

Target Latency SLA

Hard Timeout Ceiling

 

Cache Lookup & Deserialization

\< 5 ms

50 ms

HTTP/2 Fast-Path Transport (via Proxy)

\< 450 ms

3,000 ms

Stealth Headless Browser Fallback

\< 1,800 ms

6,000 ms

Selectolax DOM Parsing & Normalization

\< 15 ms

100 ms

End-to-End API Response (Uncached)

\< 650 ms

3,500 ms

End-to-End API Response (Cached)

\< 8 ms

50 ms

## 6. Subagent Delegation Triggers & Error Recovery

---

- DOM Drift Detection: If organic result extraction yields 0 results on
  an HTTP 200 response of \>10KB size, trigger the DOM Drift Alert. The
  agent must dump the unknown DOM structure to the diagnostic inspection
  sandbox, compare it against known semantic patterns, and generate
  updated fallback selectors.
- Proxy Exhaustion Protocol: If \>50% of the active proxy pool is
  quarantined due to HTTP 429 errors, dynamically throttle inbound rate
  limits, log an alert to journald, and switch to mobile fast-path
  endpoints to conserve quota.
- Self-Healing Daemon Restart: In the event of an unrecoverable worker
  panic or segmentation fault in native libraries, the usurp.service
  systemd user unit automatically initiates an isolated restart within 5
  seconds with state preserved in SQLite.

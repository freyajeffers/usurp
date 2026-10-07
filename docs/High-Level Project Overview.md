# High-Level Project Overview: usurp (Autonomous Google SERP Extraction Engine)

---

Enterprise-Grade, Self-Hosted Drop-in Replacement for SerpApi

## 1. Executive Summary & Mission Statement

---

The Autonomous Google SERP Extraction Engine (usurp) is an
enterprise-grade, privacy-first search engine results page (SERP)
extraction and normalization service designed to completely eliminate
dependency on proprietary, third-party search scraping providers such as
SerpApi, ScrapingBee, and ZenSerp.

Modern AI agents, LLM pipelines (e.g., LangChain, LlamaIndex), research
frameworks, and academic scanners require continuous, real-time
discovery of live web and scholarly knowledge. Commercial search APIs
pose severe liabilities: high per-query billing costs (\$50–\$250/month
for minimal query volumes), arbitrary rate limits, vendor lock-in, data
logging/tracking, and external network latency.

usurp re-architects search extraction as a sovereign, self-hosted,
offline-first microservice. It provides:

- 1:1 SerpApi API Compatibility: Direct drop-in replacement supporting
  identical REST parameters (q, location, hl, gl, start, num, device,
  engine) and matching JSON response schemas (organic_results,
  knowledge_graph, related_questions, pagination).
- Multi-Tiered Adaptive Transport: Blazing-fast HTTP/2 and HTTP/3
  requests using JA3/JA4 TLS fingerprint impersonation (via curl_cffi),
  seamlessly falling back to headless stealth browser pools
  (Playwright/Camoufox) only upon hostile bot challenges.
- Structural Heuristic Parsing: Robust CSS/XPath and semantic tree
  extraction resilient against Google's weekly CSS obfuscation and class
  rotation.
- Local Sovereignty & Zero Telemetry: All queries, caching, and rate
  management remain within host boundaries with zero third-party
  telemetry.
- Deterministic Caching & Concurrency: Local SQLite WAL engine
  preventing redundant search expenses and guaranteeing non-blocking
  reads/writes.

## 2. Core Architectural Philosophy & Invariants

---

- Invariant 1: 1:1 SerpApi Output Compatibility: All output JSON
  responses adhere strictly to SerpApi's standard schema
  (organic_results, knowledge_graph, related_questions, pagination).
- Invariant 3: Multi-Tiered Transport Fast-Path: 90%+ of queries execute
  via high-speed HTTP/2 TLS fast-path requests using browser TLS
  impersonation (curl_cffi), escalating to headless stealth browser
  pools only upon hostile challenge triggers.
- Invariant 4: Non-Blocking SQLite Concurrency: All SQLite connections
  must be configured with Write-Ahead Logging (PRAGMA journal_mode =
  WAL;), PRAGMA busy_timeout = 5000;, PRAGMA synchronous = NORMAL;, and
  PRAGMA mmap_size = 268435456;. Never hold write transactions open
  across network I/O or model inference calls.
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
  state is mutable, and use field/model validators for invariants.
- Invariant 9: Mature Library Reuse: Prefer the Python standard library
  and already-declared, maintained external libraries over custom
  implementations of established functionality (e.g. curl_cffi,
  selectolax, playwright, pydantic, fastapi, uvicorn). Add dependencies
  only when they materially improve correctness or security.
- Invariant 10 & 16: Tests Before Implementation & Updates: For every
  new behavior, boundary, bug fix, and phase component, write exhaustive
  unit and contract tests first. Demonstrate the test failure, implement
  only what is required, and run full quality gates before committing.
  Apply the same test-first discipline when updating existing contracts.
- Invariant 11: Full Boundary Validation: Validate every public input
  before processing and every public output before returning or
  persisting it. Validation covers types, structure, required fields,
  ranges, lengths, encodings, paths, URLs, enums, offsets, and error
  states. Fail closed with typed validation errors; never silently
  coerce malformed data.
- Invariant 12: Tooling Quality Gates: All commits touching source code
  must pass local quality gates: uv run ruff check . --fix, uv run black
  --check ., uv run mypy usurp, and uv run pytest -q. CI blocks pull
  request merges until all checks pass.
- Invariants 13, 14, 15: Atomic Commits & Documentation Currency:
  Maintain atomic commits grouping code, tests, and documentation. Keep
  README.md and root CHANGELOG.md strictly accurate for the current
  checkout. Synchronize all project runbooks, guides, and specifications
  with the active codebase, immediately pruning stale claims.

## 3. End-to-End Subsystem Topology

---

Layer

Subsystem

Primary Responsibility

Key Technologies

 

Layer 1

REST Ingress & Protocol Adapter

Exposes 1:1 SerpApi compatible endpoints (/search, /v1/search);
validates API tokens; maps parameters.

FastAPI, Pydantic v2, ASGI Uvicorn

Layer 2

Query Caching & Deduplication

Computes SHA-256 parameter hashes; resolves cache hits; manages
configurable TTLs (24h–7d); handles no_cache overrides.

SQLite 3.38+ (WAL Mode), Python Hashlib

Layer 3

Proxy Pool & Transport Manager

Maintains residential/datacenter proxy pool; routes geolocation (gl);
executes JA3/JA4 TLS impersonation; handles mobile WAP fast-paths.

curl_cffi, HTTP/2 & HTTP/3, asyncio

Layer 4

Stealth Browser Escalation Pool

Isolates headless browser workers for CAPTCHA/JS challenge mitigation;
cloaks Canvas/WebGL fingerprints; manages consent banners.

Playwright / Camoufox, Async Worker Pool

Layer 5

Semantic DOM Parser & Normalizer

Parses raw HTML DOM; extracts organic, PAA, knowledge graph, and
pagination data; validates against SerpApi schema.

Selectolax (Modest engine), lxml, Pydantic v2

Layer 6

Supervision, Metrics & Sandboxing

Oversees Linux usurp.service daemon; enforces process sandboxing; emits
journald logs and local health telemetry.

systemd, journald, pytest suite

## 4. Technology Stack & Dependency Inventory

---

- Core Language Runtime: Python 3.11+ (modern asynchronous typing,
  TaskGroups, match statements).
- HTTP & TLS Impersonation: curl_cffi (v0.7+) providing native libcurl
  bindings with automated browser TLS extension profiles (Chrome 120+,
  Safari 17).
- Browser Automation: Playwright with stealth patches or Camoufox for
  Gecko-based headless evasion.
- HTML Processing: selectolax (fastest C-based Lexbor/Modest engine)
  backed by lxml for robust fallback parsing.
- Web API Framework: FastAPI with Pydantic v2 schemas and uvicorn ASGI
  server.
- Local Storage: Embedded SQLite with WAL mode and memory-mapped reads.
- OS & Daemon Supervision: Linux systemd user units, journald structured
  logging.

## 5. Phased Implementation Roadmap Overview

---

1.  Phase 1: Request Transport, TLS/JA4 Fingerprinting & Proxy
    Orchestration — Build high-speed HTTP transport, TLS fingerprint
    masking, proxy health scoring, and mobile/WAP endpoint routing.
2.  Phase 2: Stealth Headless Browser Fallback & Anti-Bot Escalation —
    Construct the automated escalation circuit breaker, headless stealth
    browser pool, and cookie/consent banner bypass.
3.  Phase 3: Resilient Heuristic DOM Parser & SerpApi Schema
    Normalizer — Implement resilient selector trees for organic results,
    People Also Ask, Knowledge Graph, and rich snippets, outputting
    strict SerpApi JSON.
4.  Phase 4: Local Caching, Concurrency Control & Rate Limiting —
    Integrate SQLite WAL caching, token-bucket rate limiting, parameter
    hashing, and worker queue synchronization.
5.  Phase 5: REST API, Client Compatibility Layer & Systemd Sandboxing —
    Expose FastAPI endpoints, verify 1:1 drop-in compatibility with
    SerpApi client SDKs, package usurp.service user unit, and run
    benchmark fixture suites.

## 6. Security Model & Threat Mitigation

---

Threat Vector

Vulnerability Mechanism

Mitigation Architecture

 

IP Blacklisting & Shadow Banning

Burst request rates from single IPs trigger Google bot detection.

Token-bucket rate limiting per proxy; automated proxy quarantine upon
HTTP 429; sticky IP session pools.

TLS / TCP Fingerprint Detection

Standard Python requests/httpx expose identifiable cipher suites and
ALPN patterns.

Native curl_cffi spoofing exact Chrome/Firefox/Safari TLS extensions,
HTTP/2 settings frames, and header ordering.

DOM Obfuscation Drift

Google modifies CSS class hashes, breaking static string selectors.

Hierarchical relative selector graphs anchoring on stable semantic nodes
(e.g. h3, anchor tags, attribute filters) with fallback cascades.

Host Compromise & Privilege Escalation

Vulnerable dependencies in parsing stack exploited via malicious SERP
content.

Strict systemd user sandboxing (ProtectSystem=strict,
ProtectHome=read-only, NoNewPrivileges=true, restricted syscalls).

Denial of Service / Resource Exhaustion

Malformed queries cause infinite browser loops or memory leaks.

Strict per-query timeouts (3.0s HTTP, 10.0s Browser); bounded browser
pool sizes; automatic process recycling after N operations.

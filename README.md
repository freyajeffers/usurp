# usurp: Autonomous Google SERP Extraction Engine

---

Self-Hosted, Privacy-Sovereign, High-Throughput 1:1 Replacement for
SerpApi

## 1. Overview & Key Highlights

---

usurp is an autonomous, self-hosted search engine scraping and
extraction microservice designed as a complete, drop-in replacement for
commercial search APIs like SerpApi, ScrapingBee, and ZenSerp. It
empowers developers and autonomous AI agents to perform live Google
searches with zero third-party telemetry, zero per-search billing fees,
and ultra-low latency.

- 1:1 SerpApi API Compatibility: Identical query parameter semantics (q,
  gl, hl, start, num, device, engine) and verbatim JSON output format
  (organic_results, knowledge_graph, related_questions, pagination).
- Multi-Tiered Adaptive Transport: Blazing-fast HTTP/2 & HTTP/3 requests
  using browser TLS/JA4 fingerprint impersonation (via curl_cffi),
  completing 90%+ of queries in under 450ms.
- Automatic Anti-Bot Escalation: Seamless circuit-breaker failover to
  stealth headless browser pools (Playwright/Camoufox) when encountering
  CAPTCHAs, consent pages, or aggressive JavaScript challenges.
- Structural Heuristic Parsing: C-accelerated DOM extraction using
  selectolax anchoring on semantic node hierarchies rather than Google's
  volatile obfuscated CSS classes.
- Local High-Concurrency Caching: Non-blocking SQLite WAL caching engine
  with SHA-256 query hashing and configurable TTL to prevent redundant
  network fetches.
- Hardened Linux Daemonization: Packaged for unattended operation as a
  systemd user daemon with strict process sandboxing
  (ProtectSystem=strict, ProtectHome=read-only, NoNewPrivileges=true).

## 2. Quickstart Guide

---

### 2.1 Installation

```text
# Requires Python 3.14.8 and uv
uv sync --extra dev
```

The project pins Python 3.14.8 in `.python-version` and resolves the newest compatible runtime and development dependencies into `uv.lock`.

### 2.2 Starting the Service

\# Start the local ASGI server\
uvicorn usurp.main:app --host 127.0.0.1 --port 8000 --workers 2

### 2.3 Running under systemd

A hardened user-service unit is provided in `packaging/systemd/usurp.service`. Install it with the instructions in `packaging/systemd/README.txt`, then manage it with `systemctl --user`. The unit uses journald, automatic restart, private temporary storage, read-only home protection, and a restricted writable cache path.

### 2.4 Performing a Query

curl -s -G "http://127.0.0.1:8000/search" \\\
 --data-urlencode "q=quantum error correction" \\\
 --data-urlencode "gl=us" \\\
 --data-urlencode "hl=en" \\\
 --data-urlencode "api_key=your_secret_key"

## 4. SerpApi Drop-In Comparison3. Engineering Quality Gates & Invariants

---

usurp enforces strict engineering discipline across every development
phase:

- Non-Blocking SQLite Concurrency: WAL mode (PRAGMA journal_mode=WAL;,
  PRAGMA busy_timeout=5000;, PRAGMA synchronous=NORMAL;, PRAGMA
  mmap_size=268435456;).
- Explicit Public API Surface: Flat public API exported via
  \_\_init\_\_.py and \_\_all\_\_; internal sub-modules remain private.
- Pydantic-First Contracts: Pydantic v2 BaseModel schemas with strict
  validation across all boundaries.
- Mature Library Reuse: Native integration with vetted dependencies
  (curl_cffi, selectolax, playwright, fastapi).
- Test-First Development: Unit and contract tests written and verified
  failing before code implementation or modification.
- Full Boundary Validation: Fail-closed validation on all public inputs
  and outputs.
- Pre-Commit Quality Gates:

<!-- -->

- uv run ruff check . --fix
- uv run black --check .
- uv run mypy usurp
- uv run pytest -q

<!-- -->

- Atomic Commits & Documentation Currency: Code, tests, and
  documentation committed together atomically; README.md and
  CHANGELOG.md continuously synchronized with the active checkout.

##

---

Feature / Parameter

SerpApi (Commercial)

usurp (Self-Hosted)

 

Cost per 1,000 Searches

\$5.00 – \$15.00+

\$0.00 (Host & Proxy Bandwidth Only)

Data Privacy & Logging

All queries logged on vendor servers

Self-hosted deployment; configurable logging

Cached Response Latency

50 – 150 ms (Cloud Roundtrip)

\< 5 ms (Local SQLite Memory-Mapped I/O)

Fast-Path Search Latency

800 – 2,500 ms

350 – 650 ms (Local HTTP/2 TLS Transport)

Drop-in SDK Support

Native

100% Compatible via Base URL Redirect

## 5. Project Documentation Suite

---

The complete architectural specifications, developer guidelines, and
operational runbooks for usurp are published in the dedicated Google
Drive project folder:

- <a
  href="https://www.google.com/url?q=https://docs.google.com/document/d/1Mo_eUOHD-N_vGGHqUYpZVA0b0aiiLUjhPQomViIwn2Q/edit&amp;sa=D&amp;source=editors&amp;ust=1791341554720866&amp;usg=AOvVaw1v165d68z-avNugUHnGPOD"
  class="c7">High-Level Project Overview</a> — Executive summary,
  end-to-end topology, technology stack, and threat mitigation.
- <a
  href="https://www.google.com/url?q=https://docs.google.com/document/d/1ODU54nE_AfP4MXBKf5wPE6_x1_CwXndysECqCcP_IMg/edit&amp;sa=D&amp;source=editors&amp;ust=1791341554721418&amp;usg=AOvVaw2NTdwg8yJvR2LkYLPUEU0h"
  class="c7">Master Phased Implementation Plan</a> — Phase sequencing,
  cross-phase dependency graph, and definition of done.
- <a
  href="https://www.google.com/url?q=https://docs.google.com/document/d/1cDLPXAlqd2KWhIYDPNg20Lt3TYmVABJuiW6ff8vPHGg/edit&amp;sa=D&amp;source=editors&amp;ust=1791341554721967&amp;usg=AOvVaw3wFcQBlKEyUda7piigsdVW"
  class="c7">Phase-by-Phase Detailed Technical Specifications</a> —
  Granular architecture, data contracts, and verification gates for all
  5 phases.
- <a
  href="https://www.google.com/url?q=https://docs.google.com/document/d/1z72SMohhx7XD8QvmSWPF-bypjnIuXGMP54S1YTN1biI/edit&amp;sa=D&amp;source=editors&amp;ust=1791341554722516&amp;usg=AOvVaw30klvmHCZIdBh1bFGUY7oC"
  class="c7">AGENTS.md: Developer &amp; Coding Agent Guidelines</a> —
  Operational invariants, engineering discipline, TDD gates, and
  performance SLAs.
- <a
  href="https://www.google.com/url?q=https://docs.google.com/document/d/15iDTsiGAILRMKlHriUq5cdOnuif0IbG3hJheTb0s0Lc/edit&amp;sa=D&amp;source=editors&amp;ust=1791341554723021&amp;usg=AOvVaw024Kb7MMQoQNt140TjXIK1"
  class="c7">System Setup and Operational Runbooks</a> — Prerequisites,
  daemon sandboxing, test suites, and diagnostic procedures.

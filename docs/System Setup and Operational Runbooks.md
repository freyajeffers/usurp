# System Setup and Operational Runbooks: usurp

---

Autonomous Google SERP Extraction Engine (usurp) — Operations Guide

## 1. Host & Workstation Prerequisites

---

- Operating Platform: Modern Linux distribution (Ubuntu 22.04 LTS,
  Debian 12, or Fedora).
- Language Runtime: Python 3.11+ with standard virtual environment
  tooling.
- Database: Embedded SQLite 3.38+ with Write-Ahead Logging (WAL)
  support.
- Hardware: 2+ physical CPU cores, 4GB+ RAM.

## 2. Environment Configuration

---

- USURP_HOST: Network bind address (default 127.0.0.1).
- USURP_PORT: Local listening port (default 8000).
- USURP_API_KEY: Secret access token for API authentication.
- USURP_CACHE_DB_PATH: SQLite database storage location.
- USURP_CACHE_DEFAULT_TTL_HOURS: Time-to-live for cached responses
  (default 24h).
- USURP_MAX_BROWSER_WORKERS: Concurrency limit for headless browser pool
  (default 4).

## 3. Daemon Supervision and Process Sandboxing

---

The service runs under systemd user supervision with strict isolation
boundaries:

- Automatic recovery on failure with a 5-second backoff.
- Read-only home filesystem enforcement (ProtectHome=read-only).
- Isolated private temporary file spaces (PrivateTmp=true).
- Privilege escalation prevention (NoNewPrivileges=true).
- Structured log capture via journald.

## 4. Operational Verification Procedures & Quality Gates

### 4.1 Tooling Quality Gates (Invariant 12)

All developers and coding agents must pass the project static and test
quality gates locally before pushing code:

- CI workflows execute the exact same gate commands on all pull requests
  and block merges until all checks pass.

uv run ruff check . --fix (or uv run ruff check .)

uv run black --check .

uv run mypy usurp

uv run pytest -q



### 4.2 Test-First Workflow & Regression Gates (Invariants 10 & 16)

- New features and phase deliverables: Author exhaustive unit and
  contract tests first, confirm that they fail, implement only the
  required behavior, and verify the full quality gate passes.
- Code updates and bug fixes: Update or add the affected tests first to
  demonstrate the expected gap or failure before modifying production
  code.
- Static HTML fixture tests: Run uv run pytest
  tests/fixtures/test_serp_fixtures.py -q to verify DOM parsing
  resilience across 50+ real-world Google SERP fixtures.

### 4.3 Documentation & Commit Discipline (Invariants 13, 14, 15)

- Maintain atomic commits grouping code, tests, and documentation.
- Keep README.md and CHANGELOG.md continuously synchronized with active
  implementation state. Stale claims and obsolete examples must be
  removed immediately.

## 5. Diagnostic & Troubleshooting Guide

---

Issue

Probable Root Cause

Resolution

 

HTTP 429 Status

Proxy query frequency exceeded.

Trigger automatic proxy rotation and verify cooldown backoff.

Consent Interstitial

Expired consent tokens.

Trigger browser fallback to refresh consent cookies.

Zero Results Extracted

Google DOM selector drift.

Inspect HTML dump and update semantic anchor rules.

Database Lock Error

Missing WAL configuration.

Ensure PRAGMA journal_mode=WAL and 5000ms busy timeout.

Browser High Memory

Unrecycled browser instances.

Enforce context recycling every 25 searches.

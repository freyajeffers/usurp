# Development guide

## Current scaffold

The repository currently implements the first dependency slice from the project plan. It targets Python 3.14.8 and resolves current dependencies through `uv.lock`:

- `usurp.transport`: strict Pydantic v2 contracts, curl-cffi fast-path transport, device routing, consent cookies, and concurrency-safe proxy pool for Phase 1.
- `usurp.browser`: Phase 2 escalation contracts, challenge classification, and Playwright execution.
- `usurp.parser`: selectolax organic-result extraction and strict SerpApi response models.
- `usurp.cache`: asynchronous SQLite WAL cache with canonical parameter hashing and TTL expiry.
- `usurp.rate_limit`: async token-bucket rate limiter for client/proxy keys.
- `usurp.service`: transport → escalation check → parser → cache orchestration.
- `usurp.main:app`: `/search`, `/v1/search`, and `/health` FastAPI endpoints with dependency injection.
- `tests/`: contract and endpoint tests.

Browser execution uses Camoufox as the primary escalator, optional Chromium CDP as the intermediate fallback, and human review as the final fallback; rate limiting, core SERP feature extraction, systemd packaging, a 50-file representative static fixture corpus, authenticated human-review endpoints, a browser review UI, Prometheus metrics at `/metrics`, a disabled-by-default solver interface, and an opt-in official Google Programmable Search fallback are implemented and integrated. Camoufox is installed and verified on this ARM64 host; `example.com` renders successfully, while Google challenge responses remain fail-closed. Automated CAPTCHA bypass is not implemented.

## Commands

```text
uv sync --extra dev
uv run pytest -q
uv run ruff check .
uv run black --check .
uv run mypy usurp
```

Use `uv run uvicorn usurp.main:app --host 127.0.0.1 --port 8000` only for local endpoint smoke tests. The current endpoint intentionally returns no live search results.

## Dependency order

1. Phase 1 transport models and client.
2. Phase 2 browser escalation.
3. Phase 3 DOM parser and normalized response models.
4. Phase 4 SQLite cache and concurrency controls.
5. Phase 5 authenticated REST surface and systemd packaging.

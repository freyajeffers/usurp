# Phase-by-Phase Detailed Technical Specifications: usurp

---

Autonomous Google SERP Extraction Engine (usurp) — Complete Subsystem
Architecture

## Phase 1: Request Transport, TLS/JA4 Fingerprinting & Proxy Orchestration

---

### 1.1 Scope & Architectural Responsibilities

Phase 1 establishes the network foundation of usurp. It delivers a
high-speed, asynchronous HTTP transport layer capable of impersonating
modern web browsers at the TLS and HTTP/2 protocol levels to avoid
Google's initial automated bot-detection filters. It manages an
intelligent pool of forward proxies, enforces geolocation parameters,
and handles cookie lifecycle management (including automatic Google
Consent cookies).

### 1.2 Component Responsibilities

- TLS Impersonation Client (curl_cffi wrapper):

<!-- -->

- Impersonates exact browser TLS handshakes (JA3/JA4 fingerprints),
  supported cipher suites, elliptic curves, and ALPN negotiation
  matching Chrome 120+ and Safari 17.
- Enforces strict HTTP/2 protocol settings (window update frames, header
  priority trees, pseudo-header ordering :method, :authority, :scheme,
  :path).
- Implements configurable socket timeouts (default: 3.0s connect, 5.0s
  read) with automatic asynchronous cancellation.

<!-- -->

- Proxy Pool Router & Health Prober:

<!-- -->

- Maintains an active inventory of HTTP, SOCKS5, and residential proxy
  endpoints.
- Performs background health checks against lightweight probe endpoints
  (e.g. google.com/generate_204) every 60 seconds.
- Applies exponential cooldown backoff to proxies encountering HTTP 429
  (Rate Limited) or HTTP 403 (Forbidden) responses.
- Supports sticky session routing to preserve cookie consistency for
  sequential paginated queries.
- Maps Google country codes (gl=us, gl=uk, gl=de) to regional proxy exit
  nodes.

<!-- -->

- Mobile & WAP Fast-Path Router:

<!-- -->

- Provides an optional mobile user-agent execution path (iPhone Safari /
  Android Chrome) which yields cleaner, significantly smaller HTML
  payloads (often 60–75% fewer DOM nodes than desktop SERPs), reducing
  network transfer and parsing latency.

<!-- -->

- Consent & Cookie Manager:

<!-- -->

- Generates and injects synthetic Google consent cookies (e.g., SOCS and
  CONSENT tokens) into request headers, preventing European
  GDPR/ePrivacy redirect interstitials.

### 1.3 Data Contracts & Interface Schemas

\# Data Contract: Proxy Node Definition\
ProxyNode:\
 id: str (UUIDv4)\
 uri: str (e.g., "http://user:pass@host:port")\
 protocol: Enum\[HTTP, HTTPS, SOCKS5\]\
 region: str (ISO 3166-1 alpha-2, e.g., "US", "DE")\
 consecutive_failures: int\
 avg_latency_ms: float\
 is_active: bool\
 quarantined_until: Optional\[datetime\]\
\
\# Data Contract: Inbound Transport Request Context\
TransportRequest:\
 query: str\
 country_code: str (gl)\
 language_code: str (hl)\
 start_offset: int\
 num_results: int\
 time_range: Optional\[str\] (tbs parameter)\
 device_type: Enum\[DESKTOP, MOBILE\]\
 session_id: Optional\[str\]\
\
\# Data Contract: Outbound Transport Result\
TransportResult:\
 status_code: int\
 headers: dict\[str, str\]\
 raw_html: str\
 response_time_ms: float\
 proxy_used_id: Optional\[str\]\
 escalation_required: bool  # Flagged True if CAPTCHA or blocking
interstitial detected

### 1.4 Acceptance Criteria & Verification Gates

- TLS Authenticity: Outbound TLS Client Hello captured via packet
  inspection matches legitimate Google Chrome 120 JA3/JA4 fingerprints
  with 100% compliance.
- Transport Latency SLA: Average transport roundtrip under 450ms across
  standard residential/datacenter proxy connections.
- Proxy Failover Resilience: Upon receiving an induced HTTP 429 status,
  the proxy is immediately quarantined and the request successfully
  completes through an alternate proxy within 1.2s.
- Consent Bypass: Requests targeting European IP exits (e.g. gl=fr,
  gl=de) successfully bypass consent walls and return SERP HTML on first
  attempt.

## Phase 2: Stealth Headless Browser Fallback & Anti-Bot Escalation

---

### 2.1 Scope & Architectural Responsibilities

Phase 2 implements the automated escalation safety net. When Google
deploys hostile JavaScript challenges, complex cookie verification
redirects, or CAPTCHA interstitials that cannot be resolved via HTTP/2
TLS fast-paths, the system transparently escalates the query to an
isolated, headless browser pool. The browser executes in an
ultra-stealth sandbox, resolves the challenge, captures the rendered
DOM, and returns it to the pipeline.

### 2.2 Component Responsibilities

- Escalation Circuit Breaker:

<!-- -->

- Inspects raw HTML payloads from Phase 1 for challenge indicators (e.g.
  presence of /sorry/index, recaptcha,
  iframe\[src\*="google.com/recaptcha"\], or empty/truncated response
  bodies).
- Instantly triggers headless browser fallback if challenge patterns are
  verified.

<!-- -->

- Stealth Browser Pool Manager:

<!-- -->

- Maintains a bounded pool of warm, headless browser contexts
  (Playwright with Chromium or Camoufox Gecko engine).
- Enforces strict resource limits: maximum 4 concurrent browser
  instances to prevent CPU starvation on local host.
- Recycles browser contexts after 25 executions to eliminate memory
  leaks.

<!-- -->

- Browser Fingerprint Cloaking:

<!-- -->

- Strips automation artifacts (navigator.webdriver = false).
- Injects authentic Canvas, WebGL, AudioContext, and font metrics
  matching common desktop hardware.
- Emulates realistic user navigation timings (natural typing cadence,
  random mouse jiggling, smooth scroll increments).

<!-- -->

- Automated Consent Interstitial Resolver:

<!-- -->

- Detects and automatically clicks through "Reject all" or "Accept all"
  buttons on Google's consent modal dialogs.

### 2.3 Data Contracts & Interface Schemas

\# Data Contract: Escalation Request Context\
EscalationRequest:\
 target_url: str\
 proxy_uri: Optional\[str\]\
 user_agent: str\
 viewport_width: int\
 viewport_height: int\
 timeout_seconds: float (default: 8.0)\
\
\# Data Contract: Escalation Execution Result\
EscalationResult:\
 rendered_html: str\
 final_url: str\
 execution_duration_ms: float\
 challenge_type_encountered: Enum\[NONE, CONSENT_DIALOG, JS_CHALLENGE,
HARD_CAPTCHA\]\
 resolved_successfully: bool

### 2.4 Acceptance Criteria & Verification Gates

- Challenge Resolution: 100% of synthetic JavaScript and consent
  challenge pages encountered in testing are successfully resolved and
  rendered.
- Resource Containment: Peak memory consumption per headless browser
  worker strictly bounded under 450MB RSS; zero dangling browser
  processes post-execution.
- Escalation Latency Budget: Total browser resolution and DOM extraction
  completes in \<1.8s for consent flows and \<3.5s for complex JS
  challenges.

## Phase 3: Resilient Heuristic DOM Parser & SerpApi Schema Normalizer

---

### 3.1 Scope & Architectural Responsibilities

Phase 3 contains the parsing and normalization intelligence. Google
frequently changes its CSS class names to disrupt scrapers. This phase
implements a resilient, multi-tiered heuristic parser using selectolax
and lxml that anchors on structural DOM hierarchies, semantic HTML5
elements, and ARIA roles rather than volatile class names. It maps
extracted SERP elements directly into SerpApi's standard JSON schema.

### 3.2 Component Responsibilities

- Semantic Hierarchy Anchor Engine:

<!-- -->

- Locates search result clusters using relative DOM patterns (e.g. div
  \> div \> a \> h3).
- Extracts result links strictly from validated search result
  containers, filtering out internal navigation links, Google ads
  (sponsored clusters), and footer elements.

<!-- -->

- Modular Feature Extractors:

<!-- -->

- Organic Results Extractor: Extracts position (1..N), title,
  destination URL, displayed breadcrumb link, snippet description,
  publication date (if available), sitelinks, and rich attributes.
- Featured Snippet Extractor: Extracts highlighted answer boxes,
  bulleted/table summaries, and attributed source URLs.
- Knowledge Graph Extractor: Extracts entity title, subtitle/type,
  biographical descriptions, Wikipedia links, social profiles, and
  key-value attribute tables.
- People Also Ask (PAA) Extractor: Extracts collapsible questions,
  initial preview text, and referenced source links.
- Related Searches Extractor: Extracts related query strings, thumbnail
  images, and search refinement URLs.
- Pagination & Search Metadata Extractor: Extracts total estimated
  result count, search duration, current page number, and navigation
  URLs for next/previous pages.

<!-- -->

- SerpApi Normalizer:

<!-- -->

- Serializes extracted elements into Pydantic v2 data models conforming
  1:1 to SerpApi's output specification.

### 3.3 Data Contracts & Interface Schemas

\# Data Contract: SerpApi 1:1 Schema\
SerpApiResponse:\
 search_metadata:\
   id: str (UUIDv4)\
   status: str ("Success")\
   created_at: str (ISO8601)\
   processed_at: str (ISO8601)\
   total_time_taken: float\
   google_url: str\
 search_parameters:\
   engine: str ("google")\
   q: str\
   gl: str\
   hl: str\
   start: int\
   num: int\
   device: str\
 organic_results: list\[OrganicResult\]\
 knowledge_graph: Optional\[KnowledgeGraph\]\
 related_questions: Optional\[list\[RelatedQuestion\]\]\
 related_searches: Optional\[list\[RelatedSearch\]\]\
 pagination: Optional\[PaginationInfo\]\
\
OrganicResult:\
 position: int\
 title: str\
 link: str\
 displayed_link: str\
 snippet: str\
 snippet_highlighted_words: Optional\[list\[str\]\]\
 date: Optional\[str\]\
 sitelinks: Optional\[dict\[str, list\[dict\[str, str\]\]\]\]\
\
KnowledgeGraph:\
 title: str\
 type: str\
 description: Optional\[str\]\
 source: Optional\[dict\[str, str\]\]\
 attributes: Optional\[dict\[str, str\]\]\
\
RelatedQuestion:\
 question: str\
 snippet: str\
 title: str\
 link: str\
 displayed_link: str

### 3.4 Acceptance Criteria & Verification Gates

- Extraction Accuracy: ≥96% precision and recall on title, URL, snippet,
  and position across a test corpus of 100 diverse historical Google
  SERP HTML fixtures.
- Parsing Speed: DOM parsing and normalization executes in \<15ms per
  page using C-based selectolax Lexbor tree traversal.
- Schema Validation: 100% of normalized outputs pass Pydantic v2
  validation against SerpApi reference fixtures without missing required
  keys.

## Phase 4: Local Caching, Concurrency Control & Rate Limiting

---

### 4.1 Scope & Architectural Responsibilities

Phase 4 implements the data persistence, caching, and concurrency
infrastructure. To minimize unnecessary outbound network requests and
eliminate redundant costs, usurp stores normalized SERP responses in an
embedded SQLite database configured for high-concurrency non-blocking
operations. It also enforces token-bucket rate limiting to protect host
resources and proxy reputations.

### 4.2 Component Responsibilities

- SQLite WAL Caching Engine:

<!-- -->

- Configures database with PRAGMA journal_mode = WAL;, PRAGMA
  synchronous = NORMAL;, PRAGMA busy_timeout = 5000;, and PRAGMA
  mmap_size = 268435456; (256MB).
- Stores serialized SerpApi JSON responses keyed by the SHA-256 hash of
  normalized search parameters.
- Implements configurable Time-To-Live (TTL, default: 24 hours;
  customizable from 1 hour to 30 days).
- Supports cache invalidation via no_cache=true request parameter.

<!-- -->

- Parameter Canonicalizer:

<!-- -->

- Normalizes search parameter dictionaries (lowercasing query strings,
  sorting keys, trimming whitespace) prior to computing SHA-256 cache
  hashes, ensuring identical queries hit the cache regardless of
  parameter ordering.

<!-- -->

- Token-Bucket Rate Limiter:

<!-- -->

- Controls inbound request rates per client API key and outbound
  dispatch rates per proxy node.
- Smooths request spikes and prevents bursting that could trigger Google
  network blocks.

<!-- -->

- Asynchronous Queue & Worker Pool:

<!-- -->

- Employs bounded asyncio queues to serialize database writes, ensuring
  zero write contention on SQLite.

### 4.3 Data Contracts & Interface Schemas

\# Data Contract: Cache Table Schema (SQLite)\
CREATE TABLE IF NOT EXISTS serp_cache (\
 query_hash TEXT PRIMARY KEY,       -- SHA-256 of normalized parameters\
 raw_query TEXT NOT NULL,\
 parameters_json TEXT NOT NULL,\
 response_json TEXT NOT NULL,\
 created_at INTEGER NOT NULL,      -- Unix epoch milliseconds\
 expires_at INTEGER NOT NULL,      -- Unix epoch milliseconds\
 hit_count INTEGER DEFAULT 1\
);\
CREATE INDEX IF NOT EXISTS idx_serp_cache_expires ON
serp_cache(expires_at);\
\
\# Data Contract: Rate Limiter Policy\
RateLimitPolicy:\
 max_requests_per_minute: int\
 burst_capacity: int\
 per_proxy_delay_seconds: float

### 4.4 Acceptance Criteria & Verification Gates

- Cache Hit Performance: 100% cache hit rate on repeated identical
  queries within TTL; cached response retrieved and returned in \<5ms.
- Concurrency Integrity: Zero database lock errors
  (sqlite3.OperationalError: database is locked) under a load test of
  100 concurrent reading and writing workers.
- Rate Limiting Verification: Incoming requests exceeding token bucket
  capacity return standard HTTP 429 Too Many Requests with informative
  Retry-After headers.

## Phase 5: REST API, Client Compatibility Layer & Systemd Sandboxing

---

### 5.1 Scope & Architectural Responsibilities

Phase 5 unifies the entire engine into a standalone, production-ready
microservice. It provides a FastAPI REST interface that acts as a 100%
compatible drop-in replacement for the official SerpApi endpoints,
verifies authentication tokens using constant-time comparisons, packages
the daemon as a hardened Linux systemd user service, and validates
performance against end-to-end benchmarks.

### 5.2 Component Responsibilities

- FastAPI REST Gateway:

<!-- -->

- Exposes endpoints: GET /search, GET /v1/search, and POST /v1/search.
- Exposes operational endpoints: GET /health, GET /metrics, and POST
  /v1/cache/clear.
- Maps SerpApi query parameters directly to internal TransportRequest
  structures.

<!-- -->

- SerpApi SDK Drop-in Compatibility:

<!-- -->

- Allows developers using google-search-results Python library or
  serpapi npm packages to simply redirect SERPAPI_HOST or pass custom
  base URLs without changing a single line of business logic.

<!-- -->

- Authentication Middleware:

<!-- -->

- Validates api_key parameter or Authorization: Bearer headers using
  constant-time string comparisons (secrets.compare_digest) to prevent
  timing attacks.

<!-- -->

- Linux Systemd Sandboxing:

<!-- -->

- Configures systemd user service unit (usurp.service) with strict
  privilege demotion: ProtectSystem=strict, ProtectHome=read-only,
  PrivateTmp=true, NoNewPrivileges=true, and
  ReadWritePaths=/var/lib/usurp.

<!-- -->

- Comprehensive Verification Suite:

<!-- -->

- End-to-end test runner verifying queries against live Google search,
  cached records, and challenged flows.

### 5.3 Data Contracts & Interface Schemas

\# Data Contract: API Request Parameters\
ApiSearchRequest:\
 q: str (Required)\
 engine: str = "google"\
 location: Optional\[str\]\
 hl: str = "en"\
 gl: str = "us"\
 start: int = 0\
 num: int = 10\
 device: str = "desktop"\
 tbs: Optional\[str\]\
 no_cache: bool = False\
 api_key: Optional\[str\]\
\
\# Data Contract: Health & Operational Metrics\
ServiceHealthStatus:\
 status: str ("healthy" \| "degraded")\
 uptime_seconds: float\
 active_proxies_count: int\
 quarantined_proxies_count: int\
 cache_hit_ratio_24h: float\
 avg_search_latency_ms: float

### 5.4 Acceptance Criteria & Verification Gates

- Drop-in SDK Verification: Official Python google-search-results SDK
  connects to http://localhost:8000/search and executes basic,
  paginated, and advanced queries with zero modifications to client
  code.
- Daemon Supervision: Systemd unit cleanly starts, reloads, and recovers
  from induced SIGKILL crashes within 5 seconds; user lingering
  verified.
- Sandbox Compliance: Confirmed zero permission violations in journald
  under ProtectSystem=strict and ProtectHome=read-only.

## Phase 6: Cross-Phase Invariant Enforcement & Tooling Quality Gates

Every phase in this technical specification must adhere to the project's
foundational invariants:

- Invariant 4 (Non-Blocking SQLite Concurrency): All database handles
  must configure Write-Ahead Logging (PRAGMA journal_mode = WAL;),
  PRAGMA busy_timeout = 5000;, PRAGMA synchronous = NORMAL;, and PRAGMA
  mmap_size = 268435456;. Write transactions must never cross network
  I/O boundaries.
- Invariant 7 (Explicit Public API Surface): All internal sub-modules
  across phases remain private. Each package must define an
  \_\_init\_\_.py exposing primary interfaces via \_\_all\_\_. Consumers
  must not import from internal sub-modules.
- Invariant 8 (Pydantic-First Data Contracts): All schemas
  (TransportRequest, TransportResult, EscalationRequest,
  SerpApiResponse, OrganicResult, CacheRecord, ApiSearchRequest) must be
  implemented as Pydantic v2 BaseModel classes with strict validation,
  extra="forbid", and field validators for structural invariants.
- Invariant 9 (Mature Library Reuse): Leverage the standard library and
  vetted dependencies (curl_cffi, selectolax, playwright, pydantic,
  fastapi, uvicorn) instead of writing bespoke networking, parsing, or
  serialization engines.
- Invariant 10 & 16 (Tests Before Implementation & Code
  Updates): Exhaustive unit, contract, and fixture tests must be
  authored and demonstrated to fail before writing or modifying any
  phase implementation code.
- Invariant 11 (Full Boundary Validation): Every inbound parameter (q,
  gl, hl, start, num) and outbound JSON payload must undergo complete
  boundary validation, failing closed with typed errors.
- Invariant 12 (Tooling Quality Gates): Every phase milestone must pass
  the pre-commit tooling gate:

<!-- -->

- uv run ruff check . --fix
- uv run black --check .
- uv run mypy usurp
- uv run pytest -q

<!-- -->

- Invariants 13, 14 & 15 (Atomic Commits & Documentation
  Currency): Source code, tests, and documentation must be committed
  atomically in cohesive units. README.md, CHANGELOG.md, and all
  architectural runbooks must remain continuously synchronized with the
  working codebase. Stale instructions and claims must be actively
  removed.

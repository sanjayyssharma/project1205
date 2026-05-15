# Operations guide (Phase 6)

This document is the **operator-facing** summary for limits, observability, failure modes, and configuration changes without reading the whole codebase.

## Runtime components

| Component | Role |
|-----------|------|
| FastAPI (`phase4.app`) | HTTP API, CORS, request IDs, access logs, optional rate limit, `/metrics` |
| `RestaurantRepository` | Loads `restaurants.parquet` (mtime-cached per process) |
| Groq client (`phase3.groq_client`) | OpenAI-compatible chat completions with timeout + retries |

## Environment variables (quick reference)

Documented in `.env.example`. High-signal entries:

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Required for ranking when `candidate_count > 0`. Rotate in the host secret store; never commit. |
| `GROQ_MODEL` | Chat model id (change here, redeploy/restart workers). |
| `GROQ_BASE_URL` | OpenAI-compatible base URL (default Groq). |
| `GROQ_TIMEOUT_SECONDS` | Per-request HTTP timeout for Groq calls. |
| `GROQ_MAX_RETRIES` | OpenAI SDK retries with exponential backoff on transient failures. |
| `MAX_CANDIDATES_FOR_LLM` | Default cap after Phase 2 filters (API body can override `max_candidates`). |
| `LLM_MAX_PROMPT_CHARS` | Hard ceiling on system+user message size before calling Groq; returns **413** `prompt_too_large` if exceeded. |
| `LLM_MAX_TOKENS` / `LLM_TEMPERATURE` | Completion size and sampling. |
| `HF_DATASET_REVISION` | Pin dataset revision for reproducible ingest (Phase 1). |
| `RESTAURANT_SNAPSHOT_PATH` | Override Parquet path (default under `CACHE_DIR/phase1/`). |
| `CORS_ORIGINS` | Comma-separated browser origins, or `*` for permissive dev only. |
| `API_RATE_LIMIT_PER_MINUTE` | Rolling per-client limit on `POST /v1/recommendations` only; **0** disables. Client key = first `X-Forwarded-For` hop or TCP client IP. |

## Key rotation (Groq)

1. Create a new key in the Groq console.
2. Update the deployment environment (`GROQ_API_KEY`) for **all** API replicas.
3. Restart or roll pods so each process picks up the new value (`get_settings()` is cached per process).
4. Revoke the old key after traffic is healthy.

No code change is required for rotation.

## Changing model, dataset revision, or caps

- **Model / temperature / tokens:** set env vars, restart API processes. `GET /health` exposes non-secret Groq configuration flags (boolean only for key presence).
- **Dataset revision:** set `HF_DATASET_REVISION`, re-run ingest (`make ingest` or CLI), deploy the new Parquet (or update `RESTAURANT_SNAPSHOT_PATH`).
- **Candidate cap:** adjust `MAX_CANDIDATES_FOR_LLM` and/or document client use of `max_candidates` in `POST /v1/recommendations`. Larger caps increase **latency**, **cost**, and **prompt size**; keep under `LLM_MAX_PROMPT_CHARS`.

**Budget → INR mapping** is code-owned: see `phase2/budget.py` and the Phase 2 README section.

## Observability

### Request correlation

- Clients may send `X-Request-ID`; otherwise the server generates a UUID.
- The same value is returned on the response as `X-Request-ID`.

### Structured access logs

Each request logs (INFO): `request_id`, HTTP method, path, `status`, `duration_ms`. **Optional user notes are not logged verbatim**; only `notes_len` appears on the recommend path.

### Groq usage

When the provider returns `usage`, the pipeline logs `prompt_tokens`, `completion_tokens`, `total_tokens` at INFO, and successful API responses include those fields under `groq` when present.

### Metrics (`GET /metrics`)

Prometheus text exposition (in-process counters, **per replica**):

- `recommendations_completed_total` — completed recommend handlers (including empty-filter 200s).
- `recommendations_groq_fallback_total` — responses where `groq.used_fallback` is true.
- `recommendations_errors_total` — unhandled exceptions in the recommend route (500).
- `recommendations_rate_limited_total` — 429 rejections from the in-memory limiter.

Scrape from your monitoring stack or protect `/metrics` at the edge (not authenticated by default).

## Failure modes (HTTP)

| Status | `error` code | Typical cause |
|--------|----------------|----------------|
| 404 | `snapshot_not_found` | Missing or unreadable Parquet at configured path. |
| 413 | `prompt_too_large` | Serialized prompt exceeds `LLM_MAX_PROMPT_CHARS`; tighten filters or raise the limit (ops). |
| 429 | `rate_limited` | Client exceeded `API_RATE_LIMIT_PER_MINUTE`. |
| 503 | `groq_not_configured` | No `GROQ_API_KEY` while candidates exist. |
| 422 | (FastAPI validation) | Invalid JSON body / out-of-range fields. |
| 500 | `internal_error` | Unexpected exception (check server logs, not client-facing detail). |

Groq/network/parse failures on the happy path still return **200** with `groq.used_fallback: true` and template explanations when possible.

## Optional: explanation quality checks

There is **no** automated LLM-as-judge in CI. For product reviews, a lightweight rubric is:

1. Each explanation cites at least one **observable** field (cuisine, area, rating, cost) when available.
2. No restaurant appears that was not in the candidate list (enforced by Phase 3 reconciliation).
3. Rankings stay stable under fallback (deterministic order with template text).

Document human review samples periodically; static datasets drift from real-world menus and prices.

## API replicas and rate limiting

The bundled rate limiter is **in-memory per process**. Multiple replicas do **not** share state: effective limit scales roughly with replica count unless you move limiting to a shared gateway (API management, nginx, cloud WAF).

## Phase 7 — Streamlit UI

- **Deploy runbook:** [`streamlit-deploy.md`](./streamlit-deploy.md) — **recommended:** [Railway](https://railway.app) (FastAPI) + [Streamlit Cloud](https://share.streamlit.io) (UI); optional all-in-one Streamlit.
- **Railway:** repo root, **`Procfile`** + `requirements-api.txt`; set `GROQ_API_KEY`, `RESTAURANT_SNAPSHOT_PATH` on the service.
- **Streamlit (split):** Secrets `BACKEND_MODE=http`, `BACKEND_URL=https://…up.railway.app` (no Groq key in Streamlit).
- **Package:** `streamlit_app/` — `streamlit run streamlit_app/app.py` (or `make streamlit`).
- **CORS:** server-side `httpx` → usually no Streamlit origin needed on the API.
- **Health:** sidebar **Check health** or `curl {BACKEND_URL}/health`.

## Related

- [architecture-phases.md](./architecture-phases.md) — Phase 6–7 goals and sequencing.
- [adr/001-configuration-and-limits.md](./adr/001-configuration-and-limits.md) — ADR for caps and guardrails.

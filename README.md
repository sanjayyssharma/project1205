# Project1205 — Restaurant recommendations

Foundations (Phase 0), **Phase 1 data plane**, **Phase 2 retrieval**, **Phase 3 Groq LLM**, **Phase 4 HTTP backend**, **Phase 5 Next.js web UI**, **Phase 6 hardening**, and **Phase 7 Streamlit UI** for an AI-assisted restaurant recommender using structured data plus an LLM. Product scope lives in `docs/problemstatement.md`; build phases in `docs/architecture-phases.md`.

- **`phase1/`** — Hugging Face ingest, canonical `Restaurant` model, Parquet snapshot.
- **`phase2/`** — `UserPreferences` DTO, composable filters, deterministic `filter_restaurants` + cap (no LLM).
- **`phase3/`** — Groq (OpenAI-compatible) JSON rank + explanations, parser/validator, deterministic fallback.
- **`phase4/`** — FastAPI ASGI service: `POST /v1/recommendations`, `GET /health`, `GET /metrics`, CORS, structured errors (no secrets to clients).
- **`web/`** — Next.js 14 App Router UI: preference form, loading and error states, ranked results (name, cuisines, rating, cost, explanation). In dev, `next.config.mjs` rewrites `/api/backend/*` to the Phase 4 server (default `http://127.0.0.1:8000`) so the browser does not need CORS for same-origin fetches.
- **`streamlit_app/`** — Phase 7 Streamlit UI; **recommended deploy:** FastAPI on [Railway](https://railway.app) + Streamlit on [Streamlit Cloud](https://share.streamlit.io) (`BACKEND_MODE=http`). Optional all-in-one (`BACKEND_MODE=local`).
- **Phase 6** — See `docs/operations.md`: request IDs + access logs, Groq timeout/retries, prompt-size guard (413), optional rate limit (429), in-process Prometheus text metrics, ADR in `docs/adr/001-configuration-and-limits.md`.

## Requirements

- Python 3.9+ (3.11+ recommended; matches `requires-python` in `pyproject.toml`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # optional; defaults work for `check`
```

## Commands

Health check (loads and validates configuration, no network):

```bash
make check
# or
python -m restaurant_recs check
# or, after install
restaurant-recs check
```

If `.venv` exists, `make check` / `make test` use `.venv/bin/python` automatically.

Other Makefile targets: `ingest` (Phase 1), `recommend` (Phase 2 filter), `rank` (Phase 3 Groq), `api` (Phase 4 HTTP server), `streamlit` (Phase 7 UI; requires `make install-streamlit`). Pass CLI flags via `ARGS`, e.g. `make rank ARGS='--location Bangalore --cuisine Chinese --budget low'`.

### Phase 1 ingest (network required)

```bash
make install
# smoke: first N rows only, writes Parquet under .cache/restaurant_recs/phase1/
make ingest LIMIT=500
```

Or without Make:

```bash
python -m restaurant_recs ingest --limit 500
```

Use `--no-snapshot` to skip writing Parquet. Set `HF_DATASET_REVISION` in `.env` to pin a dataset revision.

### Phase 2 retrieval (uses local snapshot; no LLM)

Requires `restaurants.parquet` from ingest (default: `CACHE_DIR/phase1/restaurants.parquet`).

```bash
python -m restaurant_recs recommend --location Bangalore --cuisine Chinese --budget low --min-rating 3.5
```

Budget INR bands are documented in `phase2/budget.py`. Omit `--budget` to skip cost filtering. Use `--include-unknown-cost` with a budget to allow rows whose cost is unknown.

```bash
make recommend ARGS='--location Indiranagar --max-candidates 10'
```

### Phase 3 Groq rank + explain (network)

Requires `GROQ_API_KEY` and a local `restaurants.parquet` snapshot (from `ingest`). Uses the same filter flags as `recommend`, then calls Groq chat completions with JSON output grounded in the candidate list.

```bash
export GROQ_API_KEY=...   # or add to .env
python -m restaurant_recs rank --location Bangalore --cuisine Chinese --max-candidates 8
```

```bash
make rank ARGS='--location Indiranagar --cuisine Italian --min-rating 4.0'
```

Model and sampling are controlled via `GROQ_MODEL`, `GROQ_BASE_URL`, `LLM_TEMPERATURE`, and `LLM_MAX_TOKENS` (see `.env.example`). If Groq errors or JSON is invalid, the CLI still returns a **fallback** ranking with template explanations (always joinable to dataset rows).

### Phase 4 HTTP API (FastAPI + Uvicorn)

Runs the same pipeline as `rank`, but over HTTP for browsers and other clients. Requires `GROQ_API_KEY` when there is at least one filtered candidate (empty filter results skip the LLM and return `groq: null`).

```bash
make api
# or
python -m uvicorn phase4.app:app --reload --host 127.0.0.1 --port 8000
# or
python -m phase4
```

- **OpenAPI / docs:** http://127.0.0.1:8000/docs  
- **Health:** `GET /health` — snapshot path, existence, Groq configured (boolean only), plus Phase 6 knobs (rate limit, Groq timeout/retries, prompt cap).  
- **Metrics:** `GET /metrics` — Prometheus text format (in-process counters; scrape per replica).  
- **Recommend:** `POST /v1/recommendations` with JSON body matching `RecommendationRequest` (`location`, `budget`, `cuisine`, `min_rating`, `optional_notes`, `include_unknown_cost`, optional `max_candidates`).  
- **Errors:** JSON bodies for `404` (`snapshot_not_found`), `413` (`prompt_too_large`), `429` (`rate_limited`), `503` (`groq_not_configured`). Optional `RESTAURANT_SNAPSHOT_PATH` and `CORS_ORIGINS` in `.env`.

### Phase 5 web UI (Next.js)

Requires Node 18+ and npm. Start the API (above) in one terminal, then:

```bash
cd web
cp .env.local.example .env.local   # optional; BACKEND_URL defaults for rewrites
npm install
npm run dev
```

Open http://localhost:3000. The page calls `POST /api/backend/v1/recommendations`, which Next forwards to `BACKEND_URL` (see `web/next.config.mjs`). For production builds that call the API directly from the browser, set `CORS_ORIGINS` on the backend to include your site origin (for example `http://localhost:3000` during testing), or keep using a same-origin proxy. Map HTTP **413** / **429** responses to user-visible messages when tightening server limits.

### Phase 6 — Hardening and operations

Operator guide: **`docs/operations.md`** (limits, failure modes, key rotation, metrics). ADR: **`docs/adr/001-configuration-and-limits.md`**.

### Phase 7 — Streamlit UI

**Recommended:** **[Railway](https://railway.app) FastAPI** + **[Streamlit Cloud](https://share.streamlit.io)** — see [`docs/streamlit-deploy.md`](docs/streamlit-deploy.md). Root **`Procfile`** starts Uvicorn on `$PORT` for Railway.

**All-in-one:** Streamlit only (`BACKEND_MODE=local`); **`requirements.txt`** includes the full stack.

```bash
# Split: API on Railway (or local), Streamlit with BACKEND_MODE=http
pip install -r requirements.txt
export BACKEND_MODE=http BACKEND_URL=https://your-service.up.railway.app
streamlit run streamlit_app/app.py
```

Optional **local API:** `make api` + same env with `http://127.0.0.1:8000`.

## Configuration

Environment variables are documented in `.env.example`. Variable names map to the `Settings` class in `restaurant_recs/config.py` (pydantic-settings accepts `HF_DATASET_ID` style aliases where defined).

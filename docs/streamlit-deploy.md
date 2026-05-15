# Go live with Streamlit (Phase 7)

This guide deploys the **Streamlit UI** on [Streamlit Community Cloud](https://share.streamlit.io) and a **FastAPI backend** elsewhere. The UI only needs `BACKEND_URL`; Groq and the dataset live on the API.

**Repo:** [github.com/sanjayyssharma/project1205](https://github.com/sanjayyssharma/project1205)  
**Main file path (Streamlit Cloud):** `streamlit_app/app.py`

---

## Architecture

```text
User browser  →  Streamlit Cloud (streamlit_app/app.py)
                      ↓ httpx (server-side)
                 FastAPI API (phase4)  →  Parquet + Groq
```

There is **no database** and **no DB username/token** for Streamlit.

---

## 1. Push code to GitHub

Ensure the full project is on `main` (not only a placeholder README). **Do not commit** `.env` (it is gitignored).

```bash
git init   # if needed
git remote add origin https://github.com/sanjayyssharma/project1205.git
git add -A
git commit -m "Restaurant recommendations: API, Streamlit, docs"
git branch -M main
git push -u origin main
```

---

## 2. Deploy the API first (required)

Streamlit cannot rank restaurants without a public API.

### 2.1 Build the restaurant snapshot (once)

On a machine with network access:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-api.txt
pip install -e .
make ingest LIMIT=500   # or full ingest for production
```

Parquet default path: `.cache/restaurant_recs/phase1/restaurants.parquet`

### 2.2 Host on Render (example)

1. New **Web Service** → connect GitHub repo `project1205`.
2. **Build:** `pip install -r requirements-api.txt && pip install -e .`
3. **Start:** `uvicorn phase4.app:app --host 0.0.0.0 --port $PORT`
4. **Environment variables:**

| Variable | Required | Notes |
|----------|----------|--------|
| `GROQ_API_KEY` | Yes (when candidates exist) | [Groq console](https://console.groq.com/keys) |
| `RESTAURANT_SNAPSHOT_PATH` | Yes | Path to `restaurants.parquet` in the container |
| `GROQ_MODEL` | No | Default `llama-3.1-8b-instant` |
| `MAX_CANDIDATES_FOR_LLM` | No | Default `50` |

5. **Include Parquet in the image** (Dockerfile example):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-api.txt pyproject.toml README.md ./
COPY restaurant_recs phase1 phase2 phase3 phase4 ./
COPY .cache/restaurant_recs/phase1/restaurants.parquet /data/restaurants.parquet
RUN pip install -r requirements-api.txt && pip install -e .
ENV RESTAURANT_SNAPSHOT_PATH=/data/restaurants.parquet
CMD uvicorn phase4.app:app --host 0.0.0.0 --port ${PORT:-8000}
```

Or download Parquet at startup from a release URL and set `RESTAURANT_SNAPSHOT_PATH`.

### 2.3 Verify API

```bash
curl https://YOUR-API.onrender.com/health
```

Expect JSON with `"snapshot_exists": true` and `"groq_configured": true`.

Save the base URL, e.g. `https://your-api.onrender.com` (no `/v1` suffix).

---

## 3. Deploy Streamlit Community Cloud

1. Open [share.streamlit.io](https://share.streamlit.io) → **Create app**.
2. Repository: `sanjayyssharma/project1205`, branch `main`.
3. **Main file path:** `streamlit_app/app.py`
4. **Dependencies:** root `requirements.txt` (`streamlit`, `httpx` only).
5. **Secrets** (App settings → Secrets):

```toml
BACKEND_URL = "https://YOUR-API.onrender.com"
```

6. Deploy and open the `*.streamlit.app` URL.

### Smoke test

1. Sidebar → **Check health** → should succeed.
2. Submit preferences (e.g. Location `Bangalore`, Cuisine `North Indian`).
3. Confirm ranked results with explanations.

---

## 4. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection error / timeout | Wrong `BACKEND_URL`; API cold start (Render free tier); API not running |
| `503 groq_not_configured` | Set `GROQ_API_KEY` on the **API** service |
| `404 snapshot_not_found` | Deploy `restaurants.parquet` and set `RESTAURANT_SNAPSHOT_PATH` on API |
| `429 rate_limited` | Lower traffic or raise `API_RATE_LIMIT_PER_MINUTE` on API |
| `413 prompt_too_large` | Reduce `max_candidates` in the form or raise `LLM_MAX_PROMPT_CHARS` on API |

Streamlit uses **server-side** `httpx`, so you usually **do not** need to add the Streamlit origin to `CORS_ORIGINS` on the API.

---

## 5. Local run (before Cloud)

```bash
# Terminal 1 — API
pip install -r requirements-api.txt && pip install -e .
export GROQ_API_KEY=...
make api

# Terminal 2 — Streamlit
pip install -r requirements.txt
export BACKEND_URL=http://127.0.0.1:8000
streamlit run streamlit_app/app.py
```

Open http://localhost:8501.

---

## Related

- [operations.md](./operations.md) — limits, metrics, key rotation  
- [architecture-phases.md](./architecture-phases.md) — Phase 7 design  
- [README.md](../README.md) — full project commands

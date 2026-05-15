# Go live: Railway (backend) + Streamlit (frontend)

**Recommended production split:** run **FastAPI (Phase 4) on [Railway](https://railway.app)** and the **Streamlit UI on [Streamlit Community Cloud](https://share.streamlit.io)**. Streamlit calls your Railway URL with **server-side `httpx`** — no Groq key in Streamlit for this mode.

**Repo:** [github.com/sanjayyssharma/project1205](https://github.com/sanjayyssharma/project1205)

---

## Part A — Railway (FastAPI backend)

### Service settings

| Field | Value |
|--------|--------|
| **Root directory** | *(empty)* — repo root (folder with `pyproject.toml`, `phase4/`) |
| **Build command** | `pip install -r requirements-api.txt && pip install -e .` |
| **Start command** | `uvicorn phase4.app:app --host 0.0.0.0 --port $PORT` |

If you use a **Procfile** at repo root, Railway can pick it up; the repo includes one with the same Uvicorn command.

### Environment variables (Railway → Variables)

| Variable | Required | Notes |
|----------|----------|--------|
| `GROQ_API_KEY` | Yes | When `candidate_count > 0` |
| `RESTAURANT_SNAPSHOT_PATH` | Yes* | Path to `restaurants.parquet` **inside the container** |
| `CORS_ORIGINS` | Optional | Usually `*` is fine for split deploy if only Streamlit uses **server-side** httpx |

\* **Parquet on Railway:** (1) commit a small snapshot (not ideal for large files), (2) bake into Docker image, or (3) download from a release URL in a release-phase script and set `RESTAURANT_SNAPSHOT_PATH`. Run `make ingest LIMIT=500` locally, then upload the file to Railway volume or object storage and point the env var.

### Verify

```bash
curl https://YOUR-SERVICE.up.railway.app/health
```

Copy the **public HTTPS base URL** (no `/v1` suffix) for Streamlit.

---

## Part B — Streamlit Community Cloud (frontend)

1. [share.streamlit.io](https://share.streamlit.io) → **New app** → connect the GitHub repo.
2. **Main file path:** `streamlit_app/app.py`
3. **Secrets** (Settings → Secrets):

```toml
BACKEND_MODE = "http"
BACKEND_URL = "https://YOUR-SERVICE.up.railway.app"
```

4. Sidebar → **Mode** → **Remote HTTP API** (or rely on secrets default if you set `BACKEND_MODE` in env only — the app reads secrets first).
5. **Check health** → OK, then submit the form.

**Dependencies on Streamlit Cloud:** root `requirements.txt` includes the full stack; for **HTTP-only** split you could trim to `streamlit` + `httpx` only (faster builds) — optional optimization.

---

## Part C — All-in-one Streamlit (no Railway)

Deploy **UI + backend in one** Streamlit app (no separate API).

**Main file path:** `streamlit_app/app.py`  
**Secrets:**

```toml
GROQ_API_KEY = "your-groq-key"
BACKEND_MODE = "local"
INGEST_LIMIT = "500"
```

Sidebar **In-process (Streamlit)**. First run may ingest from Hugging Face.

---

## Architecture diagrams

**Split (Railway + Streamlit)**

```text
Browser → Streamlit Cloud (streamlit_app/app.py)
              ↓ httpx server-side
         Railway (uvicorn phase4.app)
              ↓
         Parquet + Groq
```

**All-in-one**

```text
Browser → Streamlit Cloud
              ├─ UI
              └─ RecommendationService in-process
```

---

## Secrets reference (Streamlit)

| Secret | Split (Railway) | All-in-one |
|--------|-----------------|------------|
| `BACKEND_MODE` | `http` | `local` |
| `BACKEND_URL` | Railway `https://…` | omit |
| `GROQ_API_KEY` | omit (on Railway) | Yes |
| `INGEST_LIMIT` | omit | optional |

There is **no database** username or token.

---

## Local development

**Split:**

```bash
# Terminal 1 — mimic Railway
export GROQ_API_KEY=... RESTAURANT_SNAPSHOT_PATH=...
pip install -r requirements-api.txt && pip install -e .
uvicorn phase4.app:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Streamlit
export BACKEND_MODE=http BACKEND_URL=http://127.0.0.1:8000
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

**All-in-one:** see README Phase 7.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Streamlit `Connection refused` | Wrong `BACKEND_URL`; Railway service asleep (upgrade plan or cold start) |
| `503 groq_not_configured` | Set `GROQ_API_KEY` on **Railway**, not only Streamlit |
| `404 snapshot_not_found` | Set `RESTAURANT_SNAPSHOT_PATH` on Railway + ship Parquet |

---

## Related

- [architecture-phases.md](./architecture-phases.md) — Phase 7 (Railway + Streamlit)  
- [operations.md](./operations.md)

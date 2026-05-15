# Go live on Streamlit (all-in-one)

Deploy **UI + backend in a single Streamlit app** on [Streamlit Community Cloud](https://share.streamlit.io). No separate Render/Fly API is required unless you choose split mode.

**Repo:** [github.com/sanjayyssharma/project1205](https://github.com/sanjayyssharma/project1205)  
**Main file path:** `streamlit_app/app.py`  
**Dependencies:** root `requirements.txt` (Streamlit + data + Groq stack)

---

## Architecture (default)

```text
User browser  →  Streamlit Cloud
                    ├─ streamlit_app/app.py (UI)
                    └─ RecommendationService in-process (phase4)
                           ├─ restaurants.parquet (auto-ingest if missing)
                           └─ Groq (GROQ_API_KEY in Secrets)
```

Optional **split mode:** set `BACKEND_MODE=http` and `BACKEND_URL` to a hosted FastAPI service.

---

## 1. Push to GitHub

Ensure `main` contains the full project (`.env` must not be committed).

---

## 2. Streamlit Cloud setup

1. [share.streamlit.io](https://share.streamlit.io) → **Create app** → `sanjayyssharma/project1205`.
2. **Main file path:** `streamlit_app/app.py`
3. **Secrets** (Settings → Secrets):

```toml
GROQ_API_KEY = "your-groq-key"
BACKEND_MODE = "local"
INGEST_LIMIT = "500"
```

4. Deploy. On **first run**, the app downloads a subset of the Hugging Face dataset and writes Parquet (may take a few minutes). Use sidebar **Prepare dataset** or submit a search to trigger bootstrap.

5. Sidebar **Mode:** keep **In-process (Streamlit)**. **Check health** should show `snapshot_exists: true` and `groq_configured: true`.

---

## 3. Secrets reference

| Secret | Required | Purpose |
|--------|----------|---------|
| `GROQ_API_KEY` | Yes | Groq ranking when candidates exist |
| `BACKEND_MODE` | No | `local` (default) or `http` for remote API |
| `INGEST_LIMIT` | No | Max HF rows on first ingest (default `500`) |
| `GROQ_MODEL` | No | Default `llama-3.1-8b-instant` |
| `BACKEND_URL` | Split only | Public FastAPI base URL when `BACKEND_MODE=http` |

There is **no database** username or token.

---

## 4. Optional split deploy (HTTP mode)

If you still host FastAPI elsewhere:

```toml
BACKEND_MODE = "http"
BACKEND_URL = "https://your-api.onrender.com"
```

Use `requirements-api.txt` on the API host. See earlier sections in git history or `requirements-api.txt` comments.

---

## 5. Local development

```bash
pip install -r requirements.txt
export GROQ_API_KEY=...
streamlit run streamlit_app/app.py
```

- **In-process (default):** same as Cloud; first run ingests snapshot.  
- **HTTP mode:** `export BACKEND_MODE=http BACKEND_URL=http://127.0.0.1:8000`, run `make api` in another terminal.

---

## 6. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `groq_not_configured` | Add `GROQ_API_KEY` in Streamlit Secrets, reboot app |
| `snapshot_not_found` / ingest errors | Lower `INGEST_LIMIT`, check HF network; click **Prepare dataset** |
| Slow cold start | Normal on first ingest; later runs reuse Parquet in container cache |
| `Connection refused` in HTTP mode | Use **local** mode on Cloud, or set a valid public `BACKEND_URL` |

---

## Related

- [operations.md](./operations.md)  
- [architecture-phases.md](./architecture-phases.md)

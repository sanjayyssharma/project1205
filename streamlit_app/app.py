"""
Phase 7 Streamlit UI — all-in-one (in-process backend) or remote FastAPI.

Streamlit Cloud (recommended):
  - Main file: streamlit_app/app.py
  - Secrets: GROQ_API_KEY, optional INGEST_LIMIT=500
  - BACKEND_MODE=local (default) — no separate API host required

Local split deploy:
  - BACKEND_MODE=http and BACKEND_URL=http://127.0.0.1:8000 with ``make api`` running
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import streamlit as st

from streamlit_app.client import (
    RecommendationApiError,
    configured_backend_url,
    default_backend_url,
    resolve_backend_mode,
    run_recommendations,
)
from streamlit_app.local_backend import health_local
from streamlit_app.settings_loader import apply_streamlit_secrets_to_environ, load_settings

st.set_page_config(page_title="Restaurant recommendations", layout="wide")

apply_streamlit_secrets_to_environ()
_mode_default = resolve_backend_mode()


@st.cache_resource
def _bootstrap_local_backend() -> str:
    """One-time snapshot ensure per container (ingest from HF if Parquet missing)."""
    from streamlit_app.bootstrap import ensure_snapshot

    settings = load_settings()
    path = ensure_snapshot(settings)
    return str(path)


st.title("Restaurant recommendations")
st.caption(
    "All-in-one Streamlit deploy: backend runs **in-process** by default. "
    "Set `BACKEND_MODE=http` + `BACKEND_URL` only if you host FastAPI separately."
)

with st.sidebar:
    st.subheader("Backend")
    mode = st.radio(
        "Mode",
        options=["local", "http"],
        format_func=lambda x: "In-process (Streamlit)" if x == "local" else "Remote HTTP API",
        index=0 if _mode_default == "local" else 1,
        help="Use **local** on Streamlit Cloud. Use **http** only with a separate public API.",
    )

    if mode == "local":
        st.info("Backend + UI on this app. Requires `GROQ_API_KEY` in Secrets.")
        if st.button("Prepare dataset (first run)"):
            with st.spinner("Loading Hugging Face snapshot if needed…"):
                snap = _bootstrap_local_backend()
            st.success(f"Ready: {snap}")
        else:
            try:
                snap = _bootstrap_local_backend()
                st.caption(f"Snapshot: `{snap}`")
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Dataset not ready yet: {exc}")
        base_url = ""
    else:
        default = configured_backend_url() or default_backend_url()
        base_url = st.text_input(
            "API base URL",
            value=default,
            help="Public FastAPI URL, e.g. https://your-api.onrender.com",
        )

    if st.button("Check health"):
        try:
            if mode == "local":
                st.json(health_local())
                st.success("OK")
            else:
                import httpx

                url = (base_url or default_backend_url()).rstrip("/")
                with httpx.Client(timeout=60.0) as client:
                    h = client.get(f"{url}/health")
                if h.is_success:
                    st.success("OK")
                    st.json(h.json())
                else:
                    st.error(f"HTTP {h.status_code}")
                    st.text(h.text[:2000])
        except Exception as exc:  # noqa: BLE001
            st.exception(exc)

with st.form("prefs"):
    col1, col2 = st.columns(2)
    with col1:
        location = st.text_input("Location", value="Bangalore")
        budget = st.selectbox("Budget", ["", "low", "medium", "high"], format_func=lambda x: "Any" if x == "" else x.title())
        cuisine = st.text_input("Cuisine", value="North Indian")
    with col2:
        min_rating = st.slider("Minimum rating", 0.0, 5.0, 3.5, 0.1)
        include_unknown_cost = st.checkbox("Include restaurants with unknown cost", value=True)
        max_candidates_raw = st.text_input("Max candidates (optional)", placeholder="omit for server default")
    optional_notes = st.text_area("Optional notes", placeholder="e.g. kid-friendly, quick service…")
    submitted = st.form_submit_button("Get recommendations")

if submitted:
    if not location.strip() or not cuisine.strip():
        st.error("Location and cuisine are required.")
    else:
        max_candidates: int | None
        raw_mc = str(max_candidates_raw).strip()
        if not raw_mc:
            max_candidates = None
        else:
            try:
                max_candidates = int(raw_mc)
            except ValueError:
                st.error("Max candidates must be an integer (or leave blank).")
                st.stop()

        payload = {
            "location": location.strip(),
            "budget": None if not budget else budget,
            "cuisine": cuisine.strip(),
            "min_rating": float(min_rating),
            "optional_notes": (optional_notes or "").strip(),
            "include_unknown_cost": include_unknown_cost,
            "max_candidates": max_candidates,
        }
        try:
            label = "Ranking…" if mode == "local" else "Calling API…"
            with st.spinner(label):
                if mode == "local":
                    _bootstrap_local_backend()
                data = run_recommendations(
                    payload,
                    base_url=base_url.strip() or None,
                    mode=mode,
                )
        except RecommendationApiError as exc:
            st.error(str(exc))
            if exc.body is not None and exc.body != str(exc):
                with st.expander("Error detail"):
                    st.json(exc.body if isinstance(exc.body, (dict, list)) else {"raw": exc.body})
        except Exception as exc:  # noqa: BLE001
            st.exception(exc)
        else:
            st.subheader("Results")
            c0, c1, c2 = st.columns(3)
            c0.metric("Source restaurants", data.get("source_count", "—"))
            c1.metric("Candidates", data.get("candidate_count", "—"))
            lat = data.get("llm_latency_ms")
            c2.metric("LLM latency (ms)", f"{lat:.0f}" if isinstance(lat, (int, float)) else "—")

            groq = data.get("groq")
            if isinstance(groq, dict):
                if groq.get("used_fallback"):
                    st.warning("Ranking used fallback (see `groq.detail`).")
                pt, ct = groq.get("prompt_tokens"), groq.get("completion_tokens")
                if pt is not None or ct is not None:
                    st.caption(f"Tokens (prompt / completion): {pt} / {ct}")

            summary = data.get("summary")
            if summary:
                st.markdown(f"**Summary:** {summary}")

            ranked = data.get("ranked") or []
            if not ranked:
                st.info(data.get("empty_message") or "No restaurants matched.")
            else:
                for row in ranked:
                    if not isinstance(row, dict):
                        continue
                    rank = row.get("rank", "?")
                    name = row.get("name", "—")
                    expl = row.get("explanation", "")
                    cuisines = row.get("cuisines")
                    if isinstance(cuisines, (list, tuple)):
                        cu = ", ".join(str(x) for x in cuisines)
                    else:
                        cu = str(cuisines or "—")
                    area = ", ".join(str(x) for x in (row.get("locality"), row.get("city_area")) if x) or "—"
                    rating = row.get("rating")
                    votes = row.get("votes")
                    cost = row.get("cost_for_two_inr")
                    rating_s = f"{float(rating):.1f}" if rating is not None else "—"
                    if votes is not None:
                        rating_s += f" ({votes} votes)"
                    cost_s = f"₹{int(cost):,} for two" if cost is not None else "—"
                    with st.container():
                        st.markdown(f"### #{rank} — **{name}**")
                        st.markdown(f"{area} · {rating_s} · {cost_s}")
                        st.markdown(f"**Cuisines:** {cu}")
                        st.markdown(expl)
                        st.divider()

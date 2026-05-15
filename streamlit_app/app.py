"""
Phase 7 Streamlit UI — calls Phase 4 only (server-side httpx).

Run from repo root::

    pip install -e ".[streamlit]"
    export BACKEND_URL=http://127.0.0.1:8000   # optional
    streamlit run streamlit_app/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit Cloud runs this file with `streamlit_app/` on sys.path, not the repo root.
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import streamlit as st

from streamlit_app.client import RecommendationApiError, default_backend_url, post_recommendations

st.set_page_config(page_title="Restaurant recommendations", layout="wide")
st.title("Restaurant recommendations")
st.caption(
    "Phase 7 — Python UI. Requests use **httpx** from this process to your FastAPI backend only "
    "(set `BACKEND_URL` or `API_BASE_URL`)."
)

with st.sidebar:
    st.subheader("Backend")
    default = default_backend_url()
    base_url = st.text_input("API base URL", value=default, help="Example: http://127.0.0.1:8000")
    if st.button("Check health"):
        import httpx

        try:
            with httpx.Client(timeout=10.0) as client:
                h = client.get(f"{base_url.rstrip('/')}/health")
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
                max_candidates = None
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
            with st.spinner("Calling API…"):
                data = post_recommendations(payload, base_url=base_url.strip() or None)
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
                    st.warning("Ranking used fallback (see API `groq.detail`).")
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
                    area = ", ".join(
                        str(x) for x in (row.get("locality"), row.get("city_area")) if x
                    ) or "—"
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

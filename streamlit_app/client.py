"""Server-side HTTP client for POST /v1/recommendations (no Groq or Parquet here)."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

import httpx


class RecommendationApiError(Exception):
    def __init__(self, message: str, status: int, body: Any) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def _summarize_error_body(status: int, body: Any) -> str:
    if body is not None and isinstance(body, dict):
        msg = body.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
        err = body.get("error")
        if isinstance(err, str) and err.strip():
            return f"{err.strip()} ({status})"
        detail = body.get("detail")
        if isinstance(detail, list):
            parts: List[str] = []
            for item in detail:
                if isinstance(item, dict) and "msg" in item:
                    loc = item.get("loc")
                    loc_s = f"{'.'.join(str(x) for x in loc)}: " if isinstance(loc, list) else ""
                    parts.append(f"{loc_s}{item.get('msg', item)}")
                else:
                    parts.append(json.dumps(item))
            if parts:
                return "; ".join(parts)
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return f"Request failed ({status})"


def default_backend_url() -> str:
    """Resolve API base URL: Streamlit secrets → env vars → local dev default."""
    import os

    for getter in (_backend_url_from_streamlit_secrets,):
        url = getter()
        if url:
            return url

    raw = (os.environ.get("BACKEND_URL") or os.environ.get("API_BASE_URL") or "http://127.0.0.1:8000").strip()
    return raw.rstrip("/")


def _backend_url_from_streamlit_secrets() -> Optional[str]:
    try:
        import streamlit as st

        for key in ("BACKEND_URL", "API_BASE_URL"):
            try:
                if key in st.secrets:
                    val = str(st.secrets[key]).strip()
                    if val:
                        return val.rstrip("/")
            except Exception:
                continue
    except Exception:
        pass
    return None


def is_local_backend_url(url: str) -> bool:
    u = url.lower()
    return "127.0.0.1" in u or "localhost" in u


def configured_backend_url() -> Optional[str]:
    """Non-default API URL from secrets/env only (not ``127.0.0.1`` fallback)."""
    import os

    url = _backend_url_from_streamlit_secrets()
    if url:
        return url
    env = (os.environ.get("BACKEND_URL") or os.environ.get("API_BASE_URL") or "").strip()
    return env.rstrip("/") if env else None


def resolve_backend_mode() -> str:
    """
    ``local`` — run Phase 4 ``RecommendationService`` in-process (Streamlit all-in-one).
    ``http`` — call remote FastAPI at ``BACKEND_URL``.
    """
    from streamlit_app.settings_loader import get_config_str

    mode = get_config_str("BACKEND_MODE", "").lower()
    if mode in ("http", "remote"):
        return "http"
    if mode in ("local", "inprocess", "in-process"):
        return "local"
    url = configured_backend_url()
    if url and not is_local_backend_url(url):
        return "http"
    return "local"


def run_recommendations(
    body: Dict[str, Any],
    *,
    base_url: Optional[str] = None,
    mode: Optional[str] = None,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """Recommend via in-process backend (default) or HTTP to FastAPI."""
    m = (mode or resolve_backend_mode()).lower()
    if m == "local":
        from streamlit_app.local_backend import recommend_local

        return recommend_local(body)
    return post_recommendations(body, base_url=base_url, timeout=timeout)


def post_recommendations(
    body: Dict[str, Any],
    *,
    base_url: Optional[str] = None,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """
    POST JSON to ``{base}/v1/recommendations``; return parsed JSON object on success.

    ``body`` must match the FastAPI ``RecommendationRequest`` shape (``budget`` / ``max_candidates`` may be null).
    """
    base = (base_url or default_backend_url()).rstrip("/")
    url = f"{base}/v1/recommendations"
    rid = str(uuid.uuid4())
    headers = {"Content-Type": "application/json", "X-Request-ID": rid}
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, json=body, headers=headers)
    except httpx.ConnectError as exc:
        hint = (
            f"Cannot connect to {base}. "
            "On Streamlit Cloud, set BACKEND_URL in App settings → Secrets to your **public** "
            "FastAPI URL (e.g. https://your-app.onrender.com). "
            "localhost only works when the API runs on the same machine as Streamlit."
        )
        raise RecommendationApiError(hint, 0, {"error": "connection_refused"}) from exc
    text = r.text
    try:
        parsed: Any = json.loads(text) if text else None
    except json.JSONDecodeError:
        raise RecommendationApiError(text or f"HTTP {r.status_code}", r.status_code, text) from None

    if not r.is_success:
        raise RecommendationApiError(_summarize_error_body(r.status_code, parsed), r.status_code, parsed)

    if not isinstance(parsed, dict):
        raise RecommendationApiError("Invalid JSON response", r.status_code, parsed)
    return parsed

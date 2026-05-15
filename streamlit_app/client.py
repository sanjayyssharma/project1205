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
    import os

    raw = (os.environ.get("BACKEND_URL") or os.environ.get("API_BASE_URL") or "http://127.0.0.1:8000").strip()
    return raw.rstrip("/")


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
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=body, headers=headers)
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

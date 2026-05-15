"""In-process backend (Phase 4 service) for all-in-one Streamlit deployment."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from phase4.errors import ServiceError
from phase4.schemas import RecommendationRequest
from phase4.service import RecommendationService

from streamlit_app.bootstrap import ensure_snapshot, snapshot_path
from streamlit_app.client import RecommendationApiError
from streamlit_app.settings_loader import load_settings


def recommend_local(body: Dict[str, Any]) -> Dict[str, Any]:
    """Run filter + Groq pipeline inside the Streamlit process (no HTTP)."""
    settings = load_settings()
    ensure_snapshot(settings)

    req = RecommendationRequest.model_validate(body)
    service = RecommendationService(settings)
    try:
        resp = service.recommend(req, request_id=str(uuid.uuid4()))
    except ServiceError as exc:
        raise RecommendationApiError(exc.message, exc.status_code, exc.as_body()) from exc

    return resp.model_dump(mode="json")


def health_local() -> Dict[str, Any]:
    settings = load_settings()
    path = snapshot_path(settings)
    return {
        "status": "ok",
        "mode": "local",
        "snapshot_path": str(path.resolve()),
        "snapshot_exists": path.exists(),
        "groq_configured": bool((settings.groq_api_key or "").strip()),
    }

from __future__ import annotations

import json

import pytest

from streamlit_app.client import RecommendationApiError, post_recommendations


def test_post_recommendations_success() -> None:
    body_out = {"snapshot": "/x", "source_count": 1, "candidate_count": 0, "ranked": []}

    class _FakeResp:
        status_code = 200
        text = json.dumps(body_out)
        is_success = True

    class _FakeClient:
        def __init__(self, *a, **k) -> None:
            pass

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, *a) -> None:
            return None

        def post(self, url, json=None, headers=None) -> _FakeResp:  # noqa: ANN001
            assert "/v1/recommendations" in url
            assert json["location"] == "Delhi"
            assert headers.get("X-Request-ID")
            return _FakeResp()

    import streamlit_app.client as mod

    orig = mod.httpx.Client
    mod.httpx.Client = _FakeClient  # type: ignore[misc, assignment]
    try:
        out = post_recommendations({"location": "Delhi", "cuisine": "x", "min_rating": 0.0}, base_url="http://api")
        assert out["source_count"] == 1
    finally:
        mod.httpx.Client = orig  # type: ignore[misc, assignment]


def test_post_recommendations_api_error_body() -> None:
    err_body = {"error": "groq_not_configured", "message": "No key"}

    class _FakeResp:
        status_code = 503
        text = json.dumps(err_body)
        is_success = False

    class _FakeClient:
        def __init__(self, *a, **k) -> None:
            pass

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, *a) -> None:
            return None

        def post(self, url, json=None, headers=None) -> _FakeResp:  # noqa: ANN001
            return _FakeResp()

    import streamlit_app.client as mod

    orig = mod.httpx.Client
    mod.httpx.Client = _FakeClient  # type: ignore[misc, assignment]
    try:
        with pytest.raises(RecommendationApiError) as ei:
            post_recommendations({"location": "Delhi", "cuisine": "x", "min_rating": 0.0}, base_url="http://api")
        assert ei.value.status == 503
        assert "No key" in str(ei.value)
    finally:
        mod.httpx.Client = orig  # type: ignore[misc, assignment]

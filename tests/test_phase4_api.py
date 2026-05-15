from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from phase1.pipeline import write_parquet_snapshot
from phase1.schema import Restaurant
from phase4 import metrics
from phase4.app import create_app
from phase4.rate_limit import reset_buckets
from phase3.schema import GroqRankingResult, ScoredRestaurant
from restaurant_recs.config import Settings, get_settings


def _tiny_parquet(path: Path) -> None:
    rows = [
        Restaurant(
            id="r-000001",
            name="A",
            locality="Whitefield",
            city_area="Whitefield",
            cuisines=("Chinese",),
            rating=4.5,
            votes=10,
            cost_for_two_inr=800,
        ),
        Restaurant(
            id="r-000002",
            name="B",
            locality="Indiranagar",
            city_area="Bangalore",
            cuisines=("Italian",),
            rating=4.2,
            votes=5,
            cost_for_two_inr=1200,
        ),
    ]
    write_parquet_snapshot(rows, path)


@pytest.fixture
def tiny_snapshot(tmp_path: Path) -> Path:
    p = tmp_path / "restaurants.parquet"
    _tiny_parquet(p)
    return p


@pytest.fixture
def api_client(tiny_snapshot: Path):
    get_settings.cache_clear()

    def _settings() -> Settings:
        return Settings(
            groq_api_key="dummy-key",
            restaurant_snapshot_path=tiny_snapshot,
            cors_origins="*",
        )

    app = create_app()
    app.dependency_overrides[get_settings] = _settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_health(api_client: TestClient, tiny_snapshot: Path) -> None:
    r = api_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["snapshot_exists"] is True
    assert body["snapshot_path"] == str(tiny_snapshot.resolve())


def test_recommendations_groq_not_configured(tiny_snapshot: Path) -> None:
    get_settings.cache_clear()

    def _settings() -> Settings:
        return Settings(
            groq_api_key=None,
            restaurant_snapshot_path=tiny_snapshot,
        )

    app = create_app()
    app.dependency_overrides[get_settings] = _settings
    try:
        with TestClient(app) as client:
            r = client.post("/v1/recommendations", json={"location": "Whitefield", "min_rating": 0})
        assert r.status_code == 503
        assert r.json()["error"] == "groq_not_configured"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_recommendations_snapshot_missing(tmp_path: Path) -> None:
    get_settings.cache_clear()
    missing = tmp_path / "nope.parquet"

    def _settings() -> Settings:
        return Settings(
            groq_api_key="dummy-key",
            restaurant_snapshot_path=missing,
        )

    app = create_app()
    app.dependency_overrides[get_settings] = _settings
    try:
        with TestClient(app) as client:
            r = client.post("/v1/recommendations", json={})
        assert r.status_code == 404
        assert r.json()["error"] == "snapshot_not_found"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_recommendations_empty_candidates(api_client: TestClient) -> None:
    r = api_client.post("/v1/recommendations", json={"location": "nowhere-xyz-123", "min_rating": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["candidate_count"] == 0
    assert body["ranked"] == []
    assert body["groq"] is None
    assert body["empty_message"]


@patch("phase4.service.rank_with_groq")
def test_recommendations_success(mock_rank, api_client: TestClient) -> None:
    a = Restaurant(
        id="r-000001",
        name="A",
        locality="Whitefield",
        city_area="Whitefield",
        cuisines=("Chinese",),
        rating=4.5,
        votes=10,
        cost_for_two_inr=800,
    )
    mock_rank.return_value = GroqRankingResult(
        ranked=[ScoredRestaurant(restaurant=a, rank=1, explanation="Because Chinese in Whitefield.")],
        summary="Only one match.",
        used_fallback=False,
        detail=None,
        prompt_version="t",
    )
    r = api_client.post("/v1/recommendations", json={"location": "Whitefield", "min_rating": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["candidate_count"] == 1
    assert len(body["ranked"]) == 1
    assert body["ranked"][0]["name"] == "A"
    assert body["groq"]["used_fallback"] is False
    assert body["llm_latency_ms"] is not None


def test_metrics_endpoint(api_client: TestClient) -> None:
    metrics.reset()
    r = api_client.get("/metrics")
    assert r.status_code == 200
    assert "recommendations_completed_total" in r.text
    api_client.post("/v1/recommendations", json={"location": "nowhere-xyz-123", "min_rating": 0})
    r2 = api_client.get("/metrics")
    assert "recommendations_completed_total 1" in r2.text


def test_recommendations_prompt_too_large(tiny_snapshot: Path) -> None:
    get_settings.cache_clear()
    metrics.reset()

    def _settings() -> Settings:
        return Settings(
            groq_api_key="dummy-key",
            restaurant_snapshot_path=tiny_snapshot,
            cors_origins="*",
            llm_max_prompt_chars=1300,
        )

    app = create_app()
    app.dependency_overrides[get_settings] = _settings
    try:
        with TestClient(app) as client:
            r = client.post("/v1/recommendations", json={"location": "Whitefield", "min_rating": 0})
        assert r.status_code == 413
        assert r.json()["error"] == "prompt_too_large"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_rate_limit_on_recommendations(tiny_snapshot: Path) -> None:
    get_settings.cache_clear()
    metrics.reset()
    reset_buckets()

    def _settings() -> Settings:
        return Settings(
            groq_api_key="dummy-key",
            restaurant_snapshot_path=tiny_snapshot,
            cors_origins="*",
            api_rate_limit_per_minute=2,
        )

    app = create_app()
    app.dependency_overrides[get_settings] = _settings
    try:
        with TestClient(app) as client:
            assert client.post("/v1/recommendations", json={"location": "nowhere-1", "min_rating": 0}).status_code == 200
            assert client.post("/v1/recommendations", json={"location": "nowhere-2", "min_rating": 0}).status_code == 200
            r3 = client.post("/v1/recommendations", json={"location": "nowhere-3", "min_rating": 0})
        assert r3.status_code == 429
        assert r3.json()["error"] == "rate_limited"
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        reset_buckets()

from __future__ import annotations

from unittest.mock import patch

from phase1.schema import Restaurant
from phase2.preferences import UserPreferences
from phase3.groq_client import GroqCompletionOutcome
from phase3.pipeline import rank_with_groq
from restaurant_recs.config import Settings


def _r(rid: str) -> Restaurant:
    return Restaurant(
        id=rid,
        name=rid,
        locality="Indiranagar",
        city_area="Bangalore",
        cuisines=("Italian",),
        rating=4.2,
        votes=5,
        cost_for_two_inr=800,
    )


def test_rank_with_groq_no_candidates() -> None:
    settings = Settings(groq_api_key="dummy")
    prefs = UserPreferences()
    res = rank_with_groq(prefs, [], settings=settings)
    assert res.ranked == []
    assert res.detail == "no_candidates"


def test_rank_with_groq_happy_path_mocked() -> None:
    settings = Settings(groq_api_key="dummy")
    prefs = UserPreferences(location="bangalore", cuisine="italian")
    cands = [_r("r-1"), _r("r-2")]
    payload = {
        "ranked": [
            {"restaurant_id": "r-2", "rank": 1, "explanation": "Closer to your cuisine preference."},
            {"restaurant_id": "r-1", "rank": 2, "explanation": "Also a strong match."},
        ],
        "summary": "Both fit; r-2 edges ahead.",
    }
    fake_raw = __import__("json").dumps(payload)
    with patch(
        "phase3.pipeline.groq_chat_completion_text",
        return_value=GroqCompletionOutcome(text=fake_raw, prompt_tokens=10, completion_tokens=20, total_tokens=30),
    ):
        res = rank_with_groq(prefs, cands, settings=settings)
    assert res.used_fallback is False
    assert res.summary is not None
    assert [s.restaurant.id for s in res.ranked] == ["r-2", "r-1"]
    assert res.prompt_tokens == 10
    assert res.completion_tokens == 20
    assert res.total_tokens == 30


def test_rank_with_groq_parse_error_falls_back() -> None:
    settings = Settings(groq_api_key="dummy")
    prefs = UserPreferences()
    cands = [_r("r-1")]
    with patch(
        "phase3.pipeline.groq_chat_completion_text",
        return_value=GroqCompletionOutcome(text="not json"),
    ):
        res = rank_with_groq(prefs, cands, settings=settings)
    assert res.used_fallback is True
    assert len(res.ranked) == 1
    assert res.ranked[0].restaurant.id == "r-1"

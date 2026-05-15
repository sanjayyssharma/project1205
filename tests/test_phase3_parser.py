from __future__ import annotations

import json

from phase1.schema import Restaurant
from phase2.preferences import UserPreferences
from phase3 import parser as parser_mod


def _r(rid: str, name: str = "N") -> Restaurant:
    return Restaurant(
        id=rid,
        name=name,
        locality="Indiranagar",
        city_area="Bangalore",
        cuisines=("Chinese",),
        rating=4.0,
        votes=10,
        cost_for_two_inr=600,
    )


def test_parse_ranked_payload_with_fence() -> None:
    raw = """```json
{"ranked": [{"restaurant_id": "a", "rank": 1, "explanation": "ok"}], "summary": "hi"}
```"""
    rows, summary = parser_mod.parse_ranked_payload(raw)
    assert len(rows) == 1
    assert rows[0].restaurant_id == "a"
    assert summary == "hi"


def test_validate_drops_unknown_ids_and_fills() -> None:
    c1 = _r("r-1", "A")
    c2 = _r("r-2", "B")
    prefs = UserPreferences()
    rows, _ = parser_mod.parse_ranked_payload(
        json.dumps(
            {
                "ranked": [
                    {"restaurant_id": "ghost", "rank": 1, "explanation": "bad"},
                    {"restaurant_id": "r-2", "rank": 2, "explanation": "good"},
                ]
            }
        )
    )
    ranked, used_llm = parser_mod.validate_and_reconcile(rows, [c1, c2], prefs)
    assert used_llm is True
    ids = [s.restaurant.id for s in ranked]
    assert set(ids) == {"r-1", "r-2"}
    b = next(s for s in ranked if s.restaurant.id == "r-2")
    assert b.explanation == "good"


def test_fallback_result() -> None:
    c = _r("r-1")
    prefs = UserPreferences(cuisine="Chinese")
    res = parser_mod.fallback_result(prefs, [c], detail="x", prompt_version="t")
    assert res.used_fallback is True
    assert res.ranked[0].explanation

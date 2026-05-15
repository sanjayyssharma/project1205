from __future__ import annotations

from phase1.schema import Restaurant
from phase2.preferences import UserPreferences
from phase2.retrieval import empty_candidates_message, filter_restaurants


def _r(
    *,
    rid: str,
    name: str,
    locality: str = "X",
    city_area: str = "Y",
    cuisines: tuple[str, ...] = ("Italian",),
    rating: float | None = 4.0,
    votes: int | None = 10,
    cost: int | None = 800,
) -> Restaurant:
    return Restaurant(
        id=rid,
        name=name,
        locality=locality,
        city_area=city_area,
        cuisines=cuisines,
        rating=rating,
        votes=votes,
        cost_for_two_inr=cost,
    )


def test_filter_subset_and_ordering() -> None:
    a = _r(rid="r-1", name="B", rating=4.0, votes=5, cost=400)
    b = _r(rid="r-2", name="A", rating=4.5, votes=1, cost=400)
    c = _r(rid="r-3", name="C", rating=4.5, votes=10, cost=400)
    prefs = UserPreferences(location="", budget=None, cuisine="", min_rating=0.0)
    out = filter_restaurants(prefs, [a, b, c], max_candidates=2)
    assert {x.id for x in out} <= {"r-1", "r-2", "r-3"}
    assert len(out) == 2
    # Same rating 4.5: higher votes first (c then b).
    assert out[0].id == "r-3"
    assert out[1].id == "r-2"


def test_location_and_cuisine_filters() -> None:
    rows = [
        _r(rid="1", name="P1", locality="Banashankari", city_area="Bangalore", cuisines=("Chinese",)),
        _r(rid="2", name="P2", locality="Indiranagar", city_area="Bangalore", cuisines=("Italian",)),
    ]
    prefs = UserPreferences(location="bangalore", cuisine="chinese", min_rating=0.0)
    out = filter_restaurants(prefs, rows, max_candidates=10)
    assert len(out) == 1 and out[0].id == "1"


def test_min_rating_excludes_unknown_rating() -> None:
    rows = [
        _r(rid="1", name="A", rating=None, cost=500),
        _r(rid="2", name="B", rating=4.0, cost=500),
    ]
    prefs = UserPreferences(min_rating=3.5)
    out = filter_restaurants(prefs, rows, max_candidates=10)
    assert [x.id for x in out] == ["2"]


def test_budget_low_excludes_expensive() -> None:
    rows = [
        _r(rid="1", name="Cheap", cost=400),
        _r(rid="2", name="Pricey", cost=900),
    ]
    prefs = UserPreferences(budget="low")
    out = filter_restaurants(prefs, rows, max_candidates=10)
    assert [x.id for x in out] == ["1"]


def test_empty_candidates_message() -> None:
    msg0 = empty_candidates_message(UserPreferences(), 0)
    assert "ingest" in msg0.lower()
    msg1 = empty_candidates_message(UserPreferences(location="no-such-place-xyz"), 10)
    assert "no restaurants matched" in msg1.lower()
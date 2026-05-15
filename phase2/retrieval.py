"""Bounded candidate retrieval: filter + deterministic ordering + cap."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from phase1.schema import Restaurant
from phase2.filters import matches_all
from phase2.preferences import UserPreferences


def _rank_key(restaurant: Restaurant) -> Tuple[float, int, str, str]:
    """Higher rating and votes first; stable tie-break on name and id."""
    rating = restaurant.rating if restaurant.rating is not None else -1.0
    votes = restaurant.votes if restaurant.votes is not None else -1
    return (-rating, -votes, restaurant.name, restaurant.id)


def filter_restaurants(
    prefs: UserPreferences,
    restaurants: Sequence[Restaurant],
    *,
    max_candidates: int,
) -> List[Restaurant]:
    """
    Return up to ``max_candidates`` restaurants that satisfy **all** active filters.

    Output is always a subsequence of the input list order after **re-sorting**
    filtered matches (same underlying ``Restaurant`` instances, no copies).
    """
    if max_candidates < 1:
        raise ValueError("max_candidates must be >= 1")
    matched = [r for r in restaurants if matches_all(r, prefs)]
    matched.sort(key=_rank_key)
    return matched[:max_candidates]


def empty_candidates_message(prefs: UserPreferences, source_count: int) -> str:
    """Human-readable guidance when ``filter_restaurants`` returns an empty list."""
    if source_count == 0:
        return "No restaurant data loaded. Run `python -m restaurant_recs ingest` to build a snapshot."
    return (
        "No restaurants matched your filters. Try a broader location, a different cuisine, "
        "a lower minimum rating, another budget band, or enable including unknown costs."
    )

"""Composable filter predicates (Phase 2 retrieval, no LLM)."""

from __future__ import annotations

from phase1 import normalize
from phase1.schema import Restaurant
from phase2.budget import cost_matches_budget
from phase2.preferences import UserPreferences


def matches_location(restaurant: Restaurant, location_query: str) -> bool:
    q = normalize.normalize_key_part(location_query)
    if not q:
        return True
    hay = normalize.normalize_key_part(f"{restaurant.locality} {restaurant.city_area}")
    if not hay:
        return False
    return q in hay or hay in q


def matches_cuisine(restaurant: Restaurant, cuisine_query: str) -> bool:
    q = normalize.normalize_key_part(cuisine_query)
    if not q:
        return True
    for c in restaurant.cuisines:
        token = normalize.normalize_key_part(c)
        if not token:
            continue
        if token == q or q in token or token in q:
            return True
    return False


def matches_min_rating(restaurant: Restaurant, min_rating: float) -> bool:
    if min_rating <= 0:
        return True
    if restaurant.rating is None:
        return False
    return float(restaurant.rating) >= float(min_rating)


def matches_budget(restaurant: Restaurant, prefs: UserPreferences) -> bool:
    if prefs.budget is None:
        return True
    return cost_matches_budget(
        restaurant.cost_for_two_inr,
        prefs.budget,
        include_unknown=prefs.include_unknown_cost,
    )


def matches_all(restaurant: Restaurant, prefs: UserPreferences) -> bool:
    return (
        matches_location(restaurant, prefs.location)
        and matches_cuisine(restaurant, prefs.cuisine)
        and matches_min_rating(restaurant, prefs.min_rating)
        and matches_budget(restaurant, prefs)
    )

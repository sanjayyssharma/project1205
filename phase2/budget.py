"""
Budget → INR mapping for ``approx_cost(for two people)`` (Phase 1 ``cost_for_two_inr``).

These thresholds are **explicit product choices** for this dataset (Indian metros,
roughly Zomato-style buckets). Adjust via ADR if business rules change.

Bands (inclusive of upper bound where noted):

- **low:** INR ≤ 500 for two
- **medium:** INR 501–1,200 for two
- **high:** INR ≥ 1,201 for two

Rows with unknown cost (``None``) never match a budget band unless the caller sets
``UserPreferences.include_unknown_cost`` to True (then they are treated as matching
any band — useful only when you intentionally skip cost filtering in the UI).
"""

from __future__ import annotations

from typing import Optional, Tuple

from phase2.preferences import BudgetBand

# Inclusive upper bound for low tier; medium runs (LOW_MAX_INR+1) .. MEDIUM_MAX_INR.
LOW_MAX_INR: int = 500
MEDIUM_MAX_INR: int = 1200


def band_inr_range(band: BudgetBand) -> Tuple[Optional[int], Optional[int]]:
    """Return ``(min_inclusive, max_inclusive)`` in INR for two, or open bounds as None."""
    if band == "low":
        return (0, LOW_MAX_INR)
    if band == "medium":
        return (LOW_MAX_INR + 1, MEDIUM_MAX_INR)
    return (MEDIUM_MAX_INR + 1, None)


def cost_matches_budget(
    cost_for_two_inr: Optional[int],
    band: BudgetBand,
    *,
    include_unknown: bool,
) -> bool:
    """Whether ``cost_for_two_inr`` satisfies the budget band rules."""
    if cost_for_two_inr is None:
        return bool(include_unknown)
    lo, hi = band_inr_range(band)
    if lo is not None and cost_for_two_inr < lo:
        return False
    if hi is not None and cost_for_two_inr > hi:
        return False
    return True

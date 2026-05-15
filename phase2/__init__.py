"""
Phase 2 — Retrieval: preference DTO, composable filters, deterministic cap.

See docs/architecture-phases.md. Public entry: ``filter_restaurants`` in
``phase2.retrieval`` (also exposed lazily from this package).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from phase1.schema import Restaurant
    from phase2.preferences import UserPreferences


__all__ = ["UserPreferences", "filter_restaurants", "empty_candidates_message"]


def __getattr__(name: str) -> Any:
    if name == "UserPreferences":
        from phase2.preferences import UserPreferences as _UP

        return _UP
    if name == "filter_restaurants":
        from phase2.retrieval import filter_restaurants as _fr

        return _fr
    if name == "empty_candidates_message":
        from phase2.retrieval import empty_candidates_message as _ec

        return _ec
    raise AttributeError(name)


def __dir__() -> list[str]:
    return sorted([*globals().keys(), *__all__])

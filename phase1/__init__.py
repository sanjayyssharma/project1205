"""
Phase 1 — Data plane (see docs/architecture-phases.md).

Import ``load_restaurants`` from ``phase1.pipeline`` (or use ``from phase1 import
load_restaurants`` — resolved lazily to avoid importing ``datasets`` at package import time).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from phase1.report import DataQualityReport
from phase1.schema import Restaurant

__all__ = ["Restaurant", "DataQualityReport", "load_restaurants"]

if TYPE_CHECKING:
    from pathlib import Path

    from restaurant_recs.config import Settings


def __getattr__(name: str) -> Any:
    if name == "load_restaurants":
        from phase1.pipeline import load_restaurants as _load

        return _load
    raise AttributeError(name)


def __dir__() -> list[str]:
    return sorted([*globals(), "load_restaurants"])

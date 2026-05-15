"""Lightweight data-quality summary after ingest."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List, Optional

from phase1.schema import Restaurant


@dataclass(frozen=True)
class DataQualityReport:
    dataset_id: str
    revision: Optional[str]
    rows_read: int
    rows_skipped_empty_name: int
    rows_after_dedupe: int
    null_rating: int
    null_cost_for_two_inr: int
    empty_cuisines: int

    def to_dict(self) -> dict[str, object]:
        return dict(asdict(self))


def build_report(
    *,
    dataset_id: str,
    revision: Optional[str],
    rows_read: int,
    rows_skipped_empty_name: int,
    restaurants: List[Restaurant],
) -> DataQualityReport:
    null_rating = sum(1 for r in restaurants if r.rating is None)
    null_cost = sum(1 for r in restaurants if r.cost_for_two_inr is None)
    empty_cuisines = sum(1 for r in restaurants if len(r.cuisines) == 0)
    return DataQualityReport(
        dataset_id=dataset_id,
        revision=revision,
        rows_read=rows_read,
        rows_skipped_empty_name=rows_skipped_empty_name,
        rows_after_dedupe=len(restaurants),
        null_rating=null_rating,
        null_cost_for_two_inr=null_cost,
        empty_cuisines=empty_cuisines,
    )

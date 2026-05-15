"""End-to-end Phase 1 pipeline: HF rows → ``Restaurant`` list + snapshot + report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from phase1 import normalize
from phase1.ingest import iter_raw_train_rows
from phase1.report import DataQualityReport, build_report
from phase1.schema import (
    RAW_ADDRESS,
    RAW_APPROX_COST,
    RAW_BOOK_TABLE,
    RAW_CUISINES,
    RAW_DISH_LIKED,
    RAW_LISTED_IN_CITY,
    RAW_LISTED_IN_TYPE,
    RAW_LOCATION,
    RAW_MENU_ITEM,
    RAW_NAME,
    RAW_ONLINE_ORDER,
    RAW_PHONE,
    RAW_RATE,
    RAW_REST_TYPE,
    RAW_URL,
    RAW_VOTES,
    Restaurant,
)
from restaurant_recs.config import Settings


def _draft_from_raw(raw: dict[str, Any]) -> Restaurant | None:
    name = normalize.clean_str(raw.get(RAW_NAME))
    if not name:
        return None

    locality = normalize.clean_str(raw.get(RAW_LOCATION))
    city_area = normalize.clean_str(raw.get(RAW_LISTED_IN_CITY))
    cuisines = normalize.split_cuisines(raw.get(RAW_CUISINES))
    rating = normalize.parse_rate(raw.get(RAW_RATE))
    votes = normalize.parse_votes(raw.get(RAW_VOTES))
    cost = normalize.parse_cost_inr(raw.get(RAW_APPROX_COST))

    # Placeholder id; reassigned after deterministic sort in ``load_restaurants``.
    return Restaurant(
        id="pending",
        name=name,
        locality=locality,
        city_area=city_area,
        cuisines=cuisines,
        rating=rating,
        votes=votes,
        cost_for_two_inr=cost,
        address=normalize.clean_str(raw.get(RAW_ADDRESS)),
        url=normalize.clean_str(raw.get(RAW_URL)),
        phone=normalize.clean_str(raw.get(RAW_PHONE)),
        rest_type=normalize.clean_str(raw.get(RAW_REST_TYPE)),
        dish_liked=normalize.clean_str(raw.get(RAW_DISH_LIKED)),
        menu_item=normalize.clean_str(raw.get(RAW_MENU_ITEM)),
        online_order=normalize.clean_str(raw.get(RAW_ONLINE_ORDER)),
        book_table=normalize.clean_str(raw.get(RAW_BOOK_TABLE)),
        listed_in_type=normalize.clean_str(raw.get(RAW_LISTED_IN_TYPE)),
    )


def _dedupe_key(r: Restaurant) -> tuple[str, str, str]:
    return (
        normalize.normalize_key_part(r.name),
        normalize.normalize_key_part(r.locality),
        normalize.normalize_key_part(r.address),
    )


def _pick_better(a: Restaurant, b: Restaurant) -> Restaurant:
    """Prefer higher rating, then more votes, then lexicographic name for stability."""
    ar = a.rating if a.rating is not None else -1.0
    br = b.rating if b.rating is not None else -1.0
    if ar != br:
        return a if ar > br else b
    av = a.votes or 0
    bv = b.votes or 0
    if av != bv:
        return a if av > bv else b
    return a if a.name <= b.name else b


def _dedupe(restaurants: list[Restaurant]) -> list[Restaurant]:
    best: dict[tuple[str, str, str], Restaurant] = {}
    for r in restaurants:
        k = _dedupe_key(r)
        if not k[0]:
            # Without a name key we should not happen; skip defensively.
            continue
        if k not in best:
            best[k] = r
        else:
            best[k] = _pick_better(best[k], r)
    return list(best.values())


def _sort_deterministic(restaurants: list[Restaurant]) -> list[Restaurant]:
    def sort_key(r: Restaurant) -> tuple[float, int, str, str, str]:
        rating = r.rating if r.rating is not None else -1.0
        votes = r.votes if r.votes is not None else -1
        return (-rating, -votes, r.name, r.locality, r.address)

    return sorted(restaurants, key=sort_key)


def _assign_ids(restaurants: list[Restaurant]) -> list[Restaurant]:
    out: list[Restaurant] = []
    for i, r in enumerate(restaurants, start=1):
        rid = f"r-{i:06d}"
        out.append(r.model_copy(update={"id": rid}))
    return out


def default_snapshot_path(settings: Settings) -> Path:
    root = settings.effective_cache_dir() / "phase1"
    root.mkdir(parents=True, exist_ok=True)
    return root / "restaurants.parquet"


def write_parquet_snapshot(restaurants: list[Restaurant], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in restaurants:
        d = r.model_dump()
        d["cuisines"] = ",".join(r.cuisines)
        rows.append(d)
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)


def load_restaurants_from_raw_rows(
    raw_rows: list[dict[str, Any]],
    *,
    dataset_id: str = "fixture",
    revision: str | None = None,
) -> tuple[list[Restaurant], DataQualityReport]:
    """Test helper: same normalization path without Hugging Face IO."""
    skipped = 0
    drafts: list[Restaurant] = []
    for raw in raw_rows:
        d = _draft_from_raw(raw)
        if d is None:
            skipped += 1
            continue
        drafts.append(d)
    deduped = _dedupe(drafts)
    sorted_rows = _sort_deterministic(deduped)
    final = _assign_ids(sorted_rows)
    report = build_report(
        dataset_id=dataset_id,
        revision=revision,
        rows_read=len(raw_rows),
        rows_skipped_empty_name=skipped,
        restaurants=final,
    )
    return final, report


def load_restaurants(
    settings: Settings,
    *,
    row_limit: int | None = None,
    write_snapshot: bool = True,
    snapshot_path: Path | None = None,
) -> tuple[list[Restaurant], DataQualityReport]:
    """
    Load the Zomato-style HF dataset into canonical ``Restaurant`` models.

    - Skips rows with empty ``name``.
    - Dedupes on normalized (name, locality, address), keeping the stronger rating/votes.
    - Assigns stable ``r-000001`` style ids after deterministic sorting.
    - Optionally writes a Parquet snapshot under ``cache_dir/phase1/`` (or ``snapshot_path``).
    """
    skipped = 0
    drafts: list[Restaurant] = []
    rows_read = 0

    for raw in iter_raw_train_rows(settings, row_limit=row_limit):
        rows_read += 1
        d = _draft_from_raw(raw)
        if d is None:
            skipped += 1
            continue
        drafts.append(d)

    deduped = _dedupe(drafts)
    sorted_rows = _sort_deterministic(deduped)
    final = _assign_ids(sorted_rows)

    report = build_report(
        dataset_id=settings.hf_dataset_id,
        revision=settings.hf_dataset_revision,
        rows_read=rows_read,
        rows_skipped_empty_name=skipped,
        restaurants=final,
    )

    if write_snapshot and final:
        path = snapshot_path or default_snapshot_path(settings)
        write_parquet_snapshot(final, path)
        # Small sidecar for humans / CI without opening Parquet.
        meta_path = path.with_suffix(".meta.json")
        meta_path.write_text(
            json.dumps(
                {
                    "snapshot": str(path.resolve()),
                    "rows": len(final),
                    "dataset_id": settings.hf_dataset_id,
                    "revision": settings.hf_dataset_revision,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return final, report

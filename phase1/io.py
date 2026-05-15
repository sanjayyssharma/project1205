"""Load canonical ``Restaurant`` rows from Phase 1 Parquet snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

import pandas as pd

from phase1.schema import Restaurant


def load_restaurants_parquet(path: Path) -> List[Restaurant]:
    """
    Read ``restaurants.parquet`` written by ``phase1.pipeline.write_parquet_snapshot``.

    Restores ``cuisines`` from a comma-separated column and normalizes null-like
    values for optional numeric fields.
    """
    df = pd.read_parquet(path)
    # Replace NaN/NaT with None for pydantic validation.
    records = df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")
    out: list[Restaurant] = []
    for raw in records:
        row = dict(raw)
        cuisines_val = row.get("cuisines")
        if isinstance(cuisines_val, str):
            row["cuisines"] = tuple(p.strip() for p in cuisines_val.split(",") if p.strip())
        elif cuisines_val is None:
            row["cuisines"] = ()
        elif isinstance(cuisines_val, (list, tuple)):
            row["cuisines"] = tuple(str(x).strip() for x in cuisines_val if str(x).strip())
        row = _coerce_numbers(row)
        out.append(Restaurant.model_validate(row))
    return out


def _coerce_numbers(row: dict[str, Any]) -> dict[str, Any]:
    """Best-effort coercion for parquet / numpy scalar types."""
    for key in ("rating",):
        v = row.get(key)
        if v is not None and not isinstance(v, float):
            try:
                row[key] = float(v)
            except (TypeError, ValueError):
                row[key] = None
    for key in ("votes", "cost_for_two_inr"):
        v = row.get(key)
        if v is not None and not isinstance(v, int):
            try:
                row[key] = int(v)
            except (TypeError, ValueError):
                row[key] = None
    return row

"""Ensure restaurants.parquet exists (first-run ingest on Streamlit Cloud)."""

from __future__ import annotations

import os
from pathlib import Path

from phase1.pipeline import default_snapshot_path, load_restaurants
from restaurant_recs.config import Settings


def snapshot_path(settings: Settings) -> Path:
    if settings.restaurant_snapshot_path is not None:
        return Path(settings.restaurant_snapshot_path).expanduser().resolve()
    return default_snapshot_path(settings)


def ensure_snapshot(settings: Settings, *, row_limit: int | None = None) -> Path:
    """
    Return path to Parquet snapshot, running a bounded HF ingest if missing.

    ``row_limit`` defaults to ``INGEST_LIMIT`` env (500) for faster Streamlit cold starts.
    """
    path = snapshot_path(settings)
    if path.exists():
        return path

    limit = row_limit
    if limit is None:
        raw = (os.environ.get("INGEST_LIMIT") or "500").strip()
        try:
            limit = int(raw)
        except ValueError:
            limit = 500

    path.parent.mkdir(parents=True, exist_ok=True)
    load_restaurants(settings, row_limit=limit, write_snapshot=True, snapshot_path=path)
    return path

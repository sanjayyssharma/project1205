from __future__ import annotations

from pathlib import Path

import pytest

from phase1.pipeline import write_parquet_snapshot
from phase1.schema import Restaurant
from phase1.io import load_restaurants_parquet


def test_parquet_roundtrip(tmp_path: Path) -> None:
    rows = [
        Restaurant(
            id="r-000001",
            name="Test",
            locality="Indiranagar",
            city_area="Bangalore",
            cuisines=("Italian",),
            rating=4.2,
            votes=10,
            cost_for_two_inr=800,
        )
    ]
    path = tmp_path / "r.parquet"
    write_parquet_snapshot(rows, path)
    loaded = load_restaurants_parquet(path)
    assert len(loaded) == 1
    assert loaded[0] == rows[0]

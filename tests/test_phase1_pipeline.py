from __future__ import annotations

import json
from pathlib import Path

from phase1.pipeline import load_restaurants_from_raw_rows


def test_pipeline_fixture_dedupe_and_ids() -> None:
    path = Path(__file__).parent / "fixtures" / "hf_raw_rows.json"
    raw_rows = json.loads(path.read_text(encoding="utf-8"))
    restaurants, report = load_restaurants_from_raw_rows(raw_rows)

    assert report.rows_read == 4
    assert report.rows_skipped_empty_name == 1
    assert report.rows_after_dedupe == 2

    names = {r.name for r in restaurants}
    assert names == {"Dup A", "Zebra"}

    zebra = next(r for r in restaurants if r.name == "Zebra")
    dup = next(r for r in restaurants if r.name == "Dup A")
    assert zebra.id == "r-000001"
    assert dup.id == "r-000002"
    assert dup.rating == 4.2
    assert dup.cuisines == ("Italian", "Cafe")
    assert dup.cost_for_two_inr == 500

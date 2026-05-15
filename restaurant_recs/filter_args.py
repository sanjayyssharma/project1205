"""Shared argparse helpers for snapshot + preference filters (Phase 2/3 CLI)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from phase1.io import load_restaurants_parquet
from phase1.pipeline import default_snapshot_path
from phase2.preferences import UserPreferences
from phase2.retrieval import filter_restaurants
from restaurant_recs.config import Settings


def add_snapshot_arg(parser) -> None:
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="Path to restaurants.parquet (default: cache_dir/phase1/restaurants.parquet).",
    )


def add_filter_prefs_args(parser) -> None:
    parser.add_argument("--location", default="", help="Location / area substring.")
    parser.add_argument(
        "--budget",
        choices=["low", "medium", "high"],
        default=None,
        help="Budget band using INR rules in phase2/budget.py (omit to skip).",
    )
    parser.add_argument("--cuisine", default="", help="Cuisine keyword or token.")
    parser.add_argument(
        "--min-rating",
        type=float,
        default=0.0,
        help="Minimum rating (0 keeps unrated rows).",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Optional notes passed to the LLM in Phase 3 (Phase 2 ignores them for filtering).",
    )
    parser.add_argument(
        "--include-unknown-cost",
        action="store_true",
        help="Allow rows with unknown cost to pass budget filters.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=None,
        help="Cap after sorting (default: MAX_CANDIDATES_FOR_LLM from settings).",
    )


def load_snapshot_and_filter(args, settings: Settings):
    """
    Load Parquet snapshot, build ``UserPreferences``, return filtered candidates.

    Returns ``(prefs, candidates, all_restaurants, snapshot_path)``.
    Raises ``FileNotFoundError`` if snapshot is missing.
    """
    snapshot = args.snapshot or default_snapshot_path(settings)
    if not snapshot.exists():
        raise FileNotFoundError(str(snapshot.resolve()))

    restaurants = load_restaurants_parquet(snapshot)
    prefs = UserPreferences(
        location=args.location or "",
        budget=args.budget,
        cuisine=args.cuisine or "",
        min_rating=args.min_rating,
        optional_notes=args.notes or "",
        include_unknown_cost=args.include_unknown_cost,
    )
    max_c = args.max_candidates if args.max_candidates is not None else settings.max_candidates_for_llm
    candidates = filter_restaurants(prefs, restaurants, max_candidates=max_c)
    return prefs, candidates, restaurants, snapshot


def print_snapshot_not_found(snapshot_path: str) -> None:
    err = {
        "error": "snapshot_not_found",
        "path": snapshot_path,
        "hint": "Run `python -m restaurant_recs ingest` to download data and write restaurants.parquet.",
    }
    print(json.dumps(err, indent=2), file=sys.stderr)

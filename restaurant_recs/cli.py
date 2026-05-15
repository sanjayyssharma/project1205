from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from restaurant_recs import __version__
from restaurant_recs.config import get_settings
from restaurant_recs.filter_args import (
    add_filter_prefs_args,
    add_snapshot_arg,
    load_snapshot_and_filter,
    print_snapshot_not_found,
)


def cmd_check() -> int:
    """Load configuration and print a health summary (no network, no secrets)."""
    settings = get_settings()
    payload = {
        "status": "ok",
        "version": __version__,
        "hf_dataset_id": settings.hf_dataset_id,
        "cache_dir": str(settings.effective_cache_dir()),
        "llm_provider": settings.llm_provider,
        "groq_model": settings.groq_model,
        "groq_configured": bool(settings.groq_api_key),
        "max_candidates_for_llm": settings.max_candidates_for_llm,
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Phase 1: load HF dataset, normalize to ``Restaurant``, optional Parquet snapshot."""
    from phase1.pipeline import load_restaurants

    settings = get_settings()
    snapshot_path: Path | None = args.snapshot
    restaurants, report = load_restaurants(
        settings,
        row_limit=args.limit,
        write_snapshot=not args.no_snapshot,
        snapshot_path=snapshot_path,
    )
    payload = {
        "restaurants_loaded": len(restaurants),
        "report": report.to_dict(),
    }
    if args.json_only:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(report.to_dict(), indent=2))
        print(f"restaurants_loaded={len(restaurants)}", file=sys.stderr)
        if not args.no_snapshot and restaurants:
            print(
                "snapshot written under cache (see report or .meta.json next to parquet).",
                file=sys.stderr,
            )
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    """Phase 2: load snapshot, apply preference filters, print JSON candidates (no LLM)."""
    from phase2.retrieval import empty_candidates_message

    settings = get_settings()
    try:
        prefs, candidates, restaurants, snapshot = load_snapshot_and_filter(args, settings)
    except FileNotFoundError as exc:
        print_snapshot_not_found(str(exc))
        return 1

    payload = {
        "preferences": prefs.model_dump(mode="json"),
        "snapshot": str(snapshot.resolve()),
        "source_count": len(restaurants),
        "candidate_count": len(candidates),
        "candidates": [c.model_dump(mode="json") for c in candidates],
    }
    if not candidates:
        payload["empty_message"] = empty_candidates_message(prefs, len(restaurants))
    print(json.dumps(payload, indent=2))
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    """Phase 3: Phase 2 filter + Groq JSON rank/explain (grounded in candidates)."""
    from phase2.retrieval import empty_candidates_message
    from phase3.pipeline import rank_with_groq

    settings = get_settings()
    try:
        prefs, candidates, restaurants, snapshot = load_snapshot_and_filter(args, settings)
    except FileNotFoundError as exc:
        print_snapshot_not_found(str(exc))
        return 1

    if not settings.groq_api_key:
        err = {
            "error": "groq_not_configured",
            "hint": "Set GROQ_API_KEY in your environment or `.env` (see `.env.example`).",
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    if not candidates:
        payload = {
            "preferences": prefs.model_dump(mode="json"),
            "snapshot": str(snapshot.resolve()),
            "source_count": len(restaurants),
            "candidate_count": 0,
            "empty_message": empty_candidates_message(prefs, len(restaurants)),
            "ranked": [],
        }
        print(json.dumps(payload, indent=2))
        return 0

    result = rank_with_groq(prefs, candidates, settings=settings)
    ranked_out = []
    for s in result.ranked:
        row = {"rank": s.rank, "explanation": s.explanation}
        row.update(s.restaurant.model_dump(mode="json"))
        ranked_out.append(row)

    payload = {
        "preferences": prefs.model_dump(mode="json"),
        "snapshot": str(snapshot.resolve()),
        "source_count": len(restaurants),
        "candidate_count": len(candidates),
        "groq": {
            "model": settings.groq_model,
            "base_url": settings.groq_base_url,
            "used_fallback": result.used_fallback,
            "detail": result.detail,
            "prompt_version": result.prompt_version,
        },
        "summary": result.summary,
        "ranked": ranked_out,
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="restaurant-recs",
        description="Restaurant recommendation CLI (check, ingest, Phase 2 filter, Phase 3 Groq rank).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Validate config and print a JSON health summary.")
    p_check.set_defaults(func=lambda _: cmd_check())

    p_ingest = sub.add_parser("ingest", help="Load and normalize dataset (Phase 1).")
    p_ingest.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N streaming rows (for dev/CI smoke tests).",
    )
    p_ingest.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Do not write Parquet + sidecar under the configured cache directory.",
    )
    p_ingest.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="Override Parquet output path (implies a snapshot is written unless --no-snapshot).",
    )
    p_ingest.add_argument(
        "--json-only",
        action="store_true",
        help="Print a single JSON object with report plus restaurants_loaded.",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_rec = sub.add_parser(
        "recommend",
        help="Phase 2: filter snapshot by preferences (no LLM). Prints JSON.",
    )
    add_snapshot_arg(p_rec)
    add_filter_prefs_args(p_rec)
    p_rec.set_defaults(func=cmd_recommend)

    p_rank = sub.add_parser(
        "rank",
        help="Phase 3: filter candidates then call Groq for grounded rank + explanations (JSON).",
    )
    add_snapshot_arg(p_rank)
    add_filter_prefs_args(p_rank)
    p_rank.set_defaults(func=cmd_rank)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())

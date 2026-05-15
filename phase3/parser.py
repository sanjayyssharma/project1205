"""Parse and validate Groq JSON output; reconcile with canonical candidates."""

from __future__ import annotations

import json
import re
from typing import Dict, Iterable, List, Optional, Tuple

from phase1.schema import Restaurant
from phase2.preferences import UserPreferences

from phase3.schema import GroqRankingResult, LlmRankedRow, ScoredRestaurant


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def extract_json_object(raw: str) -> str:
    """Strip optional markdown fences; return best-effort JSON object text."""
    text = raw.strip()
    m = _JSON_FENCE.search(text)
    if m:
        return m.group(1).strip()
    return text


def parse_ranked_payload(raw: str) -> Tuple[List[LlmRankedRow], Optional[str]]:
    """Parse model JSON into rows + optional summary."""
    text = extract_json_object(raw)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be an object")
    ranked_any = data.get("ranked")
    if not isinstance(ranked_any, list):
        raise ValueError("missing or invalid 'ranked' array")
    rows: List[LlmRankedRow] = []
    for item in ranked_any:
        if not isinstance(item, dict):
            continue
        rows.append(LlmRankedRow.model_validate(item))
    summary = data.get("summary")
    if summary is None or summary == "":
        summary_val: Optional[str] = None
    else:
        summary_val = str(summary)
    return rows, summary_val


def _template_explanation(prefs: UserPreferences, r: Restaurant) -> str:
    """Deterministic explanation when the model omits or hallucinates rows."""
    bits: List[str] = []
    if prefs.location:
        bits.append(f"Located in {r.locality or r.city_area}.")
    if r.cuisines:
        bits.append(f"Serves {', '.join(r.cuisines)}.")
    if r.rating is not None:
        bits.append(f"Rated {r.rating:.1f}/5.")
    if r.cost_for_two_inr is not None:
        bits.append(f"About ₹{r.cost_for_two_inr} for two.")
    if prefs.optional_notes:
        bits.append("Matches your notes where the menu and listing data support it.")
    if not bits:
        return "Matches your filters based on available structured fields."
    return " ".join(bits)


def validate_and_reconcile(
    rows: List[LlmRankedRow],
    candidates: List[Restaurant],
    prefs: UserPreferences,
) -> Tuple[List[ScoredRestaurant], bool]:
    """
    Join LLM rows back to candidates; drop unknown ids; fill missing candidates.

    Returns ``(scored, used_llm_any)`` where ``used_llm_any`` is False if no valid LLM lines survived.
    """
    by_id: Dict[str, Restaurant] = {r.id: r for r in candidates}
    picked: Dict[str, ScoredRestaurant] = {}
    used_llm = False

    for row in sorted(rows, key=lambda x: (x.rank, x.restaurant_id)):
        r = by_id.get(row.restaurant_id)
        if r is None:
            continue
        if r.id in picked:
            continue
        expl = row.explanation.strip() or _template_explanation(prefs, r)
        picked[r.id] = ScoredRestaurant(restaurant=r, rank=row.rank, explanation=expl)
        used_llm = True

    # Fill missing candidates with template explanations; assign increasing ranks after max LLM rank.
    max_rank = max((s.rank for s in picked.values()), default=0)
    next_rank = max_rank + 1
    for r in candidates:
        if r.id in picked:
            continue
        picked[r.id] = ScoredRestaurant(
            restaurant=r,
            rank=next_rank,
            explanation=_template_explanation(prefs, r),
        )
        next_rank += 1

    ordered = sorted(picked.values(), key=lambda s: (s.rank, s.restaurant.id))
    # Renormalize ranks to 1..N for stable consumer UX.
    renorm = [
        ScoredRestaurant(restaurant=s.restaurant, rank=i, explanation=s.explanation)
        for i, s in enumerate(ordered, start=1)
    ]
    return renorm, used_llm


def fallback_result(
    prefs: UserPreferences,
    candidates: List[Restaurant],
    *,
    detail: str,
    prompt_version: str,
) -> GroqRankingResult:
    """Deterministic ordering with template explanations (Groq/parse failure path)."""
    ranked: List[ScoredRestaurant] = []
    for i, r in enumerate(candidates, start=1):
        ranked.append(
            ScoredRestaurant(
                restaurant=r,
                rank=i,
                explanation=_template_explanation(prefs, r),
            )
        )
    return GroqRankingResult(
        ranked=ranked,
        summary=None,
        used_fallback=True,
        detail=detail,
        prompt_version=prompt_version,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
    )

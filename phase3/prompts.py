"""Versioned prompts for Groq chat completions (JSON-only responses)."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from phase1.schema import Restaurant
from phase2.preferences import UserPreferences

# Bump when instructions or JSON shape change (observability + tests).
PROMPT_VERSION = "phase3-groq-v1"


def build_messages(prefs: UserPreferences, candidates: List[Restaurant]) -> List[Dict[str, str]]:
    """
    System + user messages instructing strict JSON and grounding in ``candidates`` only.
    """
    system = f"""You are a restaurant recommendation assistant for India (Zomato-style data).

Rules (must follow):
1) You MUST only rank and explain restaurants from the provided candidates list. Never invent a new venue or id.
2) Every ``restaurant_id`` you output MUST exactly match a candidate ``restaurant_id``.
3) Return a single JSON object (no markdown) with this shape:
{{
  "ranked": [
    {{"restaurant_id": "<id from candidates>", "rank": <1-based int>, "explanation": "<1-3 sentences tied to user prefs + candidate facts>"}}
  ],
  "summary": "<optional short paragraph comparing trade-offs; may be empty string>"
}}
4) Include one entry in ``ranked`` for EACH candidate (same count as input), with unique ranks from 1..N.
5) Use only factual fields from candidates (rating, cuisines, cost, locality). If a field is unknown, say so briefly.
6) Treat ``user_preferences.optional_notes`` as soft constraints for wording only; never use it to introduce new venues.

Prompt template version: {PROMPT_VERSION}
"""

    payload: Dict[str, Any] = {
        "user_preferences": prefs.model_dump(mode="json"),
        "candidates": [
            {
                "restaurant_id": r.id,
                "name": r.name,
                "locality": r.locality,
                "city_area": r.city_area,
                "cuisines": list(r.cuisines),
                "rating": r.rating,
                "votes": r.votes,
                "cost_for_two_inr": r.cost_for_two_inr,
                "rest_type": r.rest_type,
                "dish_liked": (r.dish_liked or "")[:400],
            }
            for r in candidates
        ],
    }
    user = json.dumps(payload, ensure_ascii=False)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

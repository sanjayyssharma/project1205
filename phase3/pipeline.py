"""Phase 3 pipeline: Groq JSON completion → validated ranking + explanations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from phase1.schema import Restaurant
from phase2.preferences import UserPreferences

from phase3 import parser as parser_mod
from phase3.groq_client import groq_chat_completion_text
from phase3.prompts import PROMPT_VERSION, build_messages
from phase3.schema import GroqRankingResult

if TYPE_CHECKING:
    from restaurant_recs.config import Settings

logger = logging.getLogger(__name__)


def rank_with_groq(
    prefs: UserPreferences,
    candidates: List[Restaurant],
    *,
    settings: "Settings",
    messages: Optional[List[Dict[str, str]]] = None,
) -> GroqRankingResult:
    """
    Rank and explain **only** among ``candidates`` using Groq.

    If ``messages`` is provided (e.g. after a prompt-size check), it must match
    ``build_messages(prefs, candidates)`` to avoid inconsistent provider input.

    On Groq/JSON/validation failure, returns a deterministic fallback (still grounded in candidates).
    """
    if not candidates:
        return GroqRankingResult(
            ranked=[],
            summary=None,
            used_fallback=False,
            detail="no_candidates",
            prompt_version=PROMPT_VERSION,
        )

    msgs = messages if messages is not None else build_messages(prefs, candidates)
    try:
        outcome = groq_chat_completion_text(msgs, settings=settings)
    except Exception as exc:  # noqa: BLE001 — surface provider errors as fallback
        return parser_mod.fallback_result(
            prefs,
            candidates,
            detail=f"groq_error:{exc.__class__.__name__}:{exc}",
            prompt_version=PROMPT_VERSION,
        )

    if not outcome.text.strip():
        return parser_mod.fallback_result(
            prefs,
            candidates,
            detail="groq_error:empty_response",
            prompt_version=PROMPT_VERSION,
        )

    if outcome.prompt_tokens is not None or outcome.completion_tokens is not None:
        logger.info(
            "groq_usage prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            outcome.prompt_tokens,
            outcome.completion_tokens,
            outcome.total_tokens,
        )

    try:
        rows, summary = parser_mod.parse_ranked_payload(outcome.text)
    except Exception as exc:  # noqa: BLE001
        return parser_mod.fallback_result(
            prefs,
            candidates,
            detail=f"parse_error:{exc.__class__.__name__}:{exc}",
            prompt_version=PROMPT_VERSION,
        )

    ranked, used_llm = parser_mod.validate_and_reconcile(rows, candidates, prefs)
    return GroqRankingResult(
        ranked=ranked,
        summary=summary,
        used_fallback=not used_llm,
        detail=None if used_llm else "reconcile_used_templates_only",
        prompt_version=PROMPT_VERSION,
        prompt_tokens=outcome.prompt_tokens,
        completion_tokens=outcome.completion_tokens,
        total_tokens=outcome.total_tokens,
    )

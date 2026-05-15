"""Recommendation use-case orchestrating Phase 2 + Phase 3."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from phase2.preferences import UserPreferences
from phase2.retrieval import empty_candidates_message, filter_restaurants
from phase3.pipeline import rank_with_groq
from phase3.prompts import build_messages
from phase3.schema import GroqRankingResult
from restaurant_recs.config import Settings

from phase4 import metrics
from phase4.errors import GroqNotConfiguredError, PromptTooLargeError
from phase4.repository import RestaurantRepository
from phase4.schemas import GroqMetadata, RecommendationRequest, RecommendationResponse

logger = logging.getLogger(__name__)


def _messages_char_count(messages: List[Dict[str, str]]) -> int:
    return sum(len(m.get("content", "")) for m in messages)


class RecommendationService:
    """Application service: snapshot → filter → optional Groq rank."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repo = RestaurantRepository(settings)

    def recommend(self, body: RecommendationRequest, *, request_id: str) -> RecommendationResponse:
        restaurants = self._repo.list_restaurants()
        prefs = body.to_user_preferences()
        max_c = body.max_candidates if body.max_candidates is not None else self._settings.max_candidates_for_llm
        candidates = filter_restaurants(prefs, restaurants, max_candidates=max_c)

        snap = str(self._repo.snapshot_path().resolve())
        if not candidates:
            metrics.inc("recommendations_completed_total")
            return RecommendationResponse(
                snapshot=snap,
                source_count=len(restaurants),
                candidate_count=0,
                ranked=[],
                summary=None,
                groq=None,
                empty_message=empty_candidates_message(prefs, len(restaurants)),
                llm_latency_ms=None,
            )

        if not (self._settings.groq_api_key or "").strip():
            raise GroqNotConfiguredError()

        messages = build_messages(prefs, candidates)
        char_count = _messages_char_count(messages)
        if char_count > self._settings.llm_max_prompt_chars:
            raise PromptTooLargeError(
                char_count=char_count,
                char_limit=self._settings.llm_max_prompt_chars,
                candidate_count=len(candidates),
            )

        t0 = time.perf_counter()
        result = rank_with_groq(prefs, candidates, settings=self._settings, messages=messages)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        logger.info(
            "request_id=%s route=recommend source=%s candidates=%s fallback=%s latency_ms=%.1f "
            "notes_len=%s prompt_tokens=%s completion_tokens=%s",
            request_id,
            len(restaurants),
            len(candidates),
            result.used_fallback,
            latency_ms,
            len(prefs.optional_notes or ""),
            result.prompt_tokens,
            result.completion_tokens,
        )

        ranked = _serialize_ranked(result)
        groq_meta = GroqMetadata(
            model=self._settings.groq_model,
            base_url=self._settings.groq_base_url,
            used_fallback=result.used_fallback,
            detail=result.detail,
            prompt_version=result.prompt_version,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
        )

        metrics.inc("recommendations_completed_total")
        if result.used_fallback:
            metrics.inc("recommendations_groq_fallback_total")

        return RecommendationResponse(
            snapshot=snap,
            source_count=len(restaurants),
            candidate_count=len(candidates),
            ranked=ranked,
            summary=result.summary,
            groq=groq_meta,
            empty_message=None,
            llm_latency_ms=round(latency_ms, 2),
        )


def _serialize_ranked(result: GroqRankingResult) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in result.ranked:
        row: Dict[str, Any] = {"rank": s.rank, "explanation": s.explanation}
        row.update(s.restaurant.model_dump(mode="json"))
        out.append(row)
    return out

"""Structured outputs for Phase 3 (Groq) ranking + explanations."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from phase1.schema import Restaurant


class LlmRankedRow(BaseModel):
    """One row from the model JSON payload before reconciliation."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    restaurant_id: str
    rank: int = Field(ge=1)
    explanation: str = ""


class ScoredRestaurant(BaseModel):
    """Join-back to a canonical ``Restaurant`` with explanation text."""

    model_config = ConfigDict(frozen=True)

    restaurant: Restaurant
    rank: int
    explanation: str


class GroqRankingResult(BaseModel):
    """Final Phase 3 response for API/CLI consumers."""

    model_config = ConfigDict(frozen=True)

    ranked: List[ScoredRestaurant]
    summary: Optional[str] = None
    used_fallback: bool = False
    detail: Optional[str] = None
    prompt_version: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

"""Phase 4 HTTP API models (request/response contracts)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from phase2.preferences import UserPreferences

BudgetApi = Literal["low", "medium", "high"]


class RecommendationRequest(BaseModel):
    """POST /v1/recommendations body — mirrors ``UserPreferences`` + optional cap."""

    model_config = ConfigDict(str_strip_whitespace=True)

    location: str = ""
    budget: Optional[BudgetApi] = None
    cuisine: str = ""
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    optional_notes: str = ""
    include_unknown_cost: bool = False
    max_candidates: Optional[int] = Field(default=None, ge=1, le=500)

    def to_user_preferences(self) -> UserPreferences:
        return UserPreferences(
            location=self.location,
            budget=self.budget,
            cuisine=self.cuisine,
            min_rating=self.min_rating,
            optional_notes=self.optional_notes,
            include_unknown_cost=self.include_unknown_cost,
        )


class GroqMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str
    base_url: str
    used_fallback: bool
    detail: Optional[str] = None
    prompt_version: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class RecommendationResponse(BaseModel):
    """Successful recommendation payload (200)."""

    model_config = ConfigDict(frozen=True)

    snapshot: str
    source_count: int
    candidate_count: int
    ranked: List[Dict[str, Any]]
    summary: Optional[str] = None
    groq: Optional[GroqMetadata] = None
    empty_message: Optional[str] = None
    llm_latency_ms: Optional[float] = None

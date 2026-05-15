"""User preference DTO (problem statement input contract)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

BudgetBand = Literal["low", "medium", "high"]


class UserPreferences(BaseModel):
    """Structured preferences collected from the web UI / API (Phase 4)."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    location: str = Field(
        default="",
        description="Geographic hint; matched against locality and city_area (substring, case-insensitive).",
    )
    budget: Optional[BudgetBand] = Field(
        default=None,
        description="When set, filters by ``cost_for_two_inr`` using ``phase2.budget`` INR bands.",
    )
    cuisine: str = Field(default="", description="Single cuisine hint; matched against cuisine tokens.")
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    optional_notes: str = Field(
        default="",
        description="Free text for Phase 3 LLM; ignored by deterministic filters in Phase 2.",
    )
    include_unknown_cost: bool = Field(
        default=False,
        description="When True, rows with unknown cost pass budget filters if a budget is set.",
    )

    @field_validator("cuisine", "location", "optional_notes", mode="before")
    @classmethod
    def _empty_string_instead_of_none(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v)

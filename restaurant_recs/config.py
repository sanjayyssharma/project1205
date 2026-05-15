from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment (see `.env.example`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hf_dataset_id: str = Field(
        default="ManikaSaini/zomato-restaurant-recommendation",
        description="Hugging Face dataset id for restaurant rows.",
    )
    hf_dataset_revision: Optional[str] = Field(
        default=None,
        description="Optional dataset git revision for reproducible ingest (Phase 1).",
    )
    cache_dir: Path = Field(
        default=Path(".cache/restaurant_recs"),
        description="Directory for dataset cache and derived artifacts.",
    )
    llm_provider: str = Field(
        default="groq",
        description="LLM backend label (Phase 3 uses Groq when configured).",
    )
    max_candidates_for_llm: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Upper bound on restaurants passed to the LLM after filtering.",
    )
    groq_api_key: Optional[str] = Field(
        default=None,
        description="Groq API key (set GROQ_API_KEY in the environment).",
    )
    groq_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Groq chat model id (see Groq docs for available models).",
    )
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="OpenAI-compatible base URL for Groq.",
    )
    llm_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for Groq chat completions.",
    )
    llm_max_tokens: int = Field(
        default=2048,
        ge=256,
        le=32768,
        description="Max tokens for Groq chat completions (completion side).",
    )
    groq_timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=600.0,
        description="HTTP timeout (seconds) for each Groq chat completion call.",
    )
    groq_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="OpenAI client max_retries (exponential backoff on transient failures).",
    )
    llm_max_prompt_chars: int = Field(
        default=120_000,
        ge=500,
        le=500_000,
        description="Max total characters in system+user messages before calling Groq (guardrail).",
    )
    api_rate_limit_per_minute: int = Field(
        default=0,
        ge=0,
        le=10_000,
        description="Max POST /v1/recommendations per client IP per rolling minute; 0 disables.",
    )
    restaurant_snapshot_path: Optional[Path] = Field(
        default=None,
        description="Optional override path to restaurants.parquet (defaults to cache_dir/phase1/restaurants.parquet).",
    )
    cors_origins: str = Field(
        default="*",
        description="Comma-separated CORS origins, or * for permissive dev (avoid credentials with *).",
    )

    @field_validator("restaurant_snapshot_path", mode="before")
    @classmethod
    def parse_snapshot_path(cls, v: object) -> Optional[Path]:
        if v is None or v == "":
            return None
        return Path(str(v))

    @field_validator("cache_dir", mode="before")
    @classmethod
    def parse_cache_dir(cls, v: object) -> Path:
        if isinstance(v, Path):
            return v
        if v is None:
            return Path(".cache/restaurant_recs")
        return Path(str(v))

    def effective_cache_dir(self) -> Path:
        """Absolute cache path for logging and health checks."""
        return self.cache_dir.expanduser().resolve()

    def cors_allow_origins(self) -> list[str]:
        """Origins for ``CORSMiddleware`` (``*`` or comma-separated list)."""
        s = self.cors_origins.strip()
        if s == "*":
            return ["*"]
        return [x.strip() for x in s.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (reload process to pick up env changes)."""
    return Settings()

"""Domain errors surfaced as structured HTTP responses (Phase 4)."""

from __future__ import annotations

from typing import Any, Dict, Optional


class ServiceError(Exception):
    """Base class for API-layer failures with stable ``error`` codes."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def as_body(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {"error": self.code, "message": self.message}
        body.update(self.details)
        return body


class SnapshotNotFoundError(ServiceError):
    def __init__(self, path: str) -> None:
        super().__init__(
            code="snapshot_not_found",
            message="Restaurant snapshot parquet is missing.",
            status_code=404,
            details={"path": path},
        )


class GroqNotConfiguredError(ServiceError):
    def __init__(self) -> None:
        super().__init__(
            code="groq_not_configured",
            message="GROQ_API_KEY is not configured on the server.",
            status_code=503,
            details={"hint": "Set GROQ_API_KEY in the API process environment."},
        )


class PromptTooLargeError(ServiceError):
    """Serialized prompt to Groq exceeds configured limit (reduce candidates or notes)."""

    def __init__(self, *, char_count: int, char_limit: int, candidate_count: int) -> None:
        super().__init__(
            code="prompt_too_large",
            message="The request would produce a prompt larger than the server allows.",
            status_code=413,
            details={
                "char_count": char_count,
                "char_limit": char_limit,
                "candidate_count": candidate_count,
                "hint": "Lower max_candidates, tighten filters, or raise LLM_MAX_PROMPT_CHARS (ops).",
            },
        )


class RateLimitedError(ServiceError):
    def __init__(self, *, limit_per_minute: int) -> None:
        super().__init__(
            code="rate_limited",
            message="Too many requests; try again later.",
            status_code=429,
            details={"limit_per_minute": limit_per_minute},
        )

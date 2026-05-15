"""Groq LLM adapter (OpenAI-compatible Chat Completions API)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, cast

from restaurant_recs.config import Settings


@dataclass(frozen=True)
class GroqCompletionOutcome:
    """Assistant text plus optional usage from the provider (Phase 6 observability)."""

    text: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


def groq_chat_completion_text(
    messages: List[dict[str, str]],
    *,
    settings: Settings,
) -> GroqCompletionOutcome:
    """
    Call Groq chat completions and return assistant message content as text.

    Uses configurable timeout and retries (exponential backoff via the OpenAI SDK).
    Prefers JSON object mode; falls back to plain completion if the provider rejects the parameter.
    """
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your environment or `.env` file for Phase 3."
        )

    from openai import OpenAI

    client = cast(
        Any,
        OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            timeout=settings.groq_timeout_seconds,
            max_retries=settings.groq_max_retries,
        ),
    )
    base_kwargs: dict[str, Any] = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    try:
        resp = client.chat.completions.create(
            **base_kwargs,
            response_format={"type": "json_object"},
        )
    except Exception:
        resp = client.chat.completions.create(**base_kwargs)
    choice0 = resp.choices[0]
    msg = choice0.message
    text = (msg.content or "").strip()
    usage = getattr(resp, "usage", None)
    pt: Optional[int] = None
    ct: Optional[int] = None
    tt: Optional[int] = None
    if usage is not None:
        pt = getattr(usage, "prompt_tokens", None)
        ct = getattr(usage, "completion_tokens", None)
        tt = getattr(usage, "total_tokens", None)
    return GroqCompletionOutcome(text=text, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt)

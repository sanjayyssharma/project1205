"""
Phase 3 — LLM integration (Groq).

Import ``rank_with_groq`` from ``phase3.pipeline`` (lazy via ``__getattr__``).
"""

from __future__ import annotations

from typing import Any

__all__ = ["rank_with_groq", "GroqRankingResult", "PROMPT_VERSION"]


def __getattr__(name: str) -> Any:
    if name == "rank_with_groq":
        from phase3.pipeline import rank_with_groq as _fn

        return _fn
    if name == "GroqRankingResult":
        from phase3.schema import GroqRankingResult as _GR

        return _GR
    if name == "PROMPT_VERSION":
        from phase3.prompts import PROMPT_VERSION as _pv

        return _pv
    raise AttributeError(name)


def __dir__() -> list[str]:
    return sorted([*globals().keys(), *__all__])

"""Parse and normalize raw dataset strings into typed fields."""

from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"\s+")


def clean_str(value: object) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return s


def normalize_key_part(value: object) -> str:
    """Lowercase, collapse whitespace, Unicode NFC — used for dedupe keys only."""
    s = clean_str(value)
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s).casefold()
    return _WS_RE.sub(" ", s).strip()


def parse_rate(value: object) -> float | None:
    """Parse values like ``4.1/5``; unknown sentinels become ``None``."""
    s = clean_str(value)
    if not s or s in {"-", "new", "none", "nan"}:
        return None
    if "/" in s:
        left = s.split("/", 1)[0].strip()
        try:
            return float(left)
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_cost_inr(value: object) -> int | None:
    """Extract integer INR from strings like ``800`` or ``Rs 1,200``."""
    s = clean_str(value)
    if not s:
        return None
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def split_cuisines(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    s = clean_str(value)
    if not s:
        return ()
    parts = [p.strip() for p in s.split(",")]
    return tuple(p for p in parts if p)


def parse_votes(value: object) -> int | None:
    if value is None:
        return None
    try:
        v = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if v < 0:
        return 0
    return v

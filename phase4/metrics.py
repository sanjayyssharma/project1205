"""In-process counters for basic observability (Phase 6)."""

from __future__ import annotations

import threading
from typing import Dict

_lock = threading.Lock()
_counters: Dict[str, int] = {
    "recommendations_completed_total": 0,
    "recommendations_groq_fallback_total": 0,
    "recommendations_errors_total": 0,
    "recommendations_rate_limited_total": 0,
}


def reset() -> None:
    """Reset counters (for tests)."""
    with _lock:
        for k in _counters:
            _counters[k] = 0


def inc(name: str, delta: int = 1) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0) + delta


def snapshot() -> Dict[str, int]:
    with _lock:
        return dict(_counters)


def prometheus_text() -> str:
    lines: list[str] = []
    with _lock:
        snap = dict(_counters)
    help_type = [
        ("recommendations_completed_total", "counter", "Completed POST /v1/recommendations handlers"),
        ("recommendations_groq_fallback_total", "counter", "Responses where Groq path used template fallback"),
        ("recommendations_errors_total", "counter", "Unhandled or service errors during recommend"),
        ("recommendations_rate_limited_total", "counter", "Requests rejected with 429 rate limit"),
    ]
    for name, typ, help_txt in help_type:
        lines.append(f"# HELP {name} {help_txt}")
        lines.append(f"# TYPE {name} {typ}")
        lines.append(f"{name} {snap.get(name, 0)}")
    return "\n".join(lines) + "\n"

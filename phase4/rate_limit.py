"""Simple in-memory sliding-window rate limit (Phase 6; per process)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict

_lock = threading.Lock()
_window_sec = 60.0
_buckets: DefaultDict[str, Deque[float]] = defaultdict(deque)


def allow(client_key: str, limit_per_minute: int) -> bool:
    """
    Return True if the request is allowed.

    ``limit_per_minute`` <= 0 disables limiting. At most ``limit_per_minute``
    requests per rolling ``_window_sec`` are allowed per ``client_key``.
    """
    if limit_per_minute <= 0:
        return True
    now = time.monotonic()
    with _lock:
        dq = _buckets[client_key]
        while dq and now - dq[0] > _window_sec:
            dq.popleft()
        if len(dq) >= limit_per_minute:
            return False
        dq.append(now)
        return True


def reset_buckets() -> None:
    """Clear all client windows (for tests)."""
    with _lock:
        _buckets.clear()

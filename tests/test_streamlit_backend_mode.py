from __future__ import annotations

import os

from streamlit_app.client import resolve_backend_mode


def test_resolve_backend_mode_local_default(monkeypatch) -> None:
    monkeypatch.delenv("BACKEND_URL", raising=False)
    monkeypatch.delenv("BACKEND_MODE", raising=False)
    assert resolve_backend_mode() == "local"


def test_resolve_backend_mode_http_explicit(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_MODE", "http")
    monkeypatch.setenv("BACKEND_URL", "https://api.example.com")
    assert resolve_backend_mode() == "http"


def test_resolve_backend_mode_public_url_without_mode(monkeypatch) -> None:
    monkeypatch.delenv("BACKEND_MODE", raising=False)
    monkeypatch.setenv("BACKEND_URL", "https://api.example.com")
    assert resolve_backend_mode() == "http"

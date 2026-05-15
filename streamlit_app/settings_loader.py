"""Load Settings from env + Streamlit secrets (all-in-one Streamlit deploy)."""

from __future__ import annotations

import os
from typing import Any, Optional

from restaurant_recs.config import Settings


def apply_streamlit_secrets_to_environ() -> None:
    """Copy ``st.secrets`` string values into ``os.environ`` for pydantic-settings."""
    try:
        import streamlit as st
    except ImportError:
        return

    try:
        secrets = st.secrets
    except Exception:
        return

    def _has(k: str) -> bool:
        try:
            return k in secrets
        except Exception:
            return False

    for key in (
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "GROQ_BASE_URL",
        "BACKEND_URL",
        "API_BASE_URL",
        "BACKEND_MODE",
        "RESTAURANT_SNAPSHOT_PATH",
        "CACHE_DIR",
        "HF_DATASET_ID",
        "HF_DATASET_REVISION",
        "INGEST_LIMIT",
        "MAX_CANDIDATES_FOR_LLM",
        "LLM_MAX_PROMPT_CHARS",
    ):
        if _has(key):
            val = secrets[key]
            if val is not None and str(val).strip() != "":
                os.environ[key] = str(val).strip()


def get_config_str(key: str, default: str = "") -> str:
    apply_streamlit_secrets_to_environ()
    try:
        import streamlit as st

        try:
            if key in st.secrets:
                return str(st.secrets[key]).strip()
        except Exception:
            pass
    except Exception:
        pass
    return (os.environ.get(key) or default).strip()


def load_settings() -> Settings:
    apply_streamlit_secrets_to_environ()
    return Settings()

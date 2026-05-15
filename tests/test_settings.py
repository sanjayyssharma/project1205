import pytest

from restaurant_recs.config import Settings


def test_settings_defaults() -> None:
    s = Settings()
    assert "zomato" in s.hf_dataset_id.lower()
    assert s.llm_provider == "groq"
    assert s.groq_model
    assert "groq" in s.groq_base_url.lower()
    assert s.max_candidates_for_llm == 50
    assert s.cache_dir.parts[-2:] == (".cache", "restaurant_recs")


def test_max_candidates_bounds() -> None:
    with pytest.raises(Exception):
        Settings(max_candidates_for_llm=0)
    with pytest.raises(Exception):
        Settings(max_candidates_for_llm=501)


def test_phase6_groq_and_rate_limit_defaults() -> None:
    s = Settings()
    assert s.groq_timeout_seconds == 60.0
    assert s.groq_max_retries == 3
    assert s.llm_max_prompt_chars == 120_000
    assert s.api_rate_limit_per_minute == 0

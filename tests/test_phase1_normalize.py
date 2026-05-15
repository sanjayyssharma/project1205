from __future__ import annotations

import pytest

from phase1 import normalize


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("4.1/5", 4.1),
        ("3", 3.0),
        ("-", None),
        ("NEW", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_rate(raw: object, expected: float | None) -> None:
    assert normalize.parse_rate(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("800", 800),
        ("Rs 1,200 for two", 1200),
        ("", None),
        (None, None),
    ],
)
def test_parse_cost_inr(raw: object, expected: int | None) -> None:
    assert normalize.parse_cost_inr(raw) == expected


def test_split_cuisines() -> None:
    assert normalize.split_cuisines("A, B ,,C") == ("A", "B", "C")


def test_normalize_key_part() -> None:
    assert normalize.normalize_key_part("  Hello   World ") == "hello world"

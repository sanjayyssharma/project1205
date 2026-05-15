"""Hugging Face dataset iteration (streaming by default)."""

from __future__ import annotations

from typing import Any, Iterator

from datasets import load_dataset

from restaurant_recs.config import Settings


def iter_raw_train_rows(
    settings: Settings,
    *,
    row_limit: int | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Yield raw row dicts from the ``train`` split.

    Uses ``streaming=True`` to avoid loading ~575MB into RAM at once.
    ``HF_DATASET_REVISION`` (when set) pins a git revision for reproducibility.
    """
    ds = load_dataset(
        settings.hf_dataset_id,
        split="train",
        streaming=True,
        revision=settings.hf_dataset_revision,
    )
    it = iter(ds)
    n = 0
    while True:
        if row_limit is not None and n >= row_limit:
            break
        try:
            row = next(it)
        except StopIteration:
            break
        # ``datasets`` streaming rows are dict-like mapping column -> value.
        yield dict(row)
        n += 1

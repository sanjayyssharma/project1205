"""Load canonical restaurants from the Phase 1 Parquet snapshot (repository)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from phase1.io import load_restaurants_parquet
from phase1.schema import Restaurant
from phase1.pipeline import default_snapshot_path
from phase4.errors import SnapshotNotFoundError
from restaurant_recs.config import Settings

logger = logging.getLogger(__name__)


class RestaurantRepository:
    """
    Read-only access to ``Restaurant`` rows with simple (path, mtime) caching.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: Optional[Tuple[Path, float, List[Restaurant]]] = None

    def snapshot_path(self) -> Path:
        if self._settings.restaurant_snapshot_path is not None:
            return Path(self._settings.restaurant_snapshot_path).expanduser().resolve()
        return default_snapshot_path(self._settings)

    def list_restaurants(self) -> List[Restaurant]:
        path = self.snapshot_path()
        if not path.exists():
            raise SnapshotNotFoundError(str(path))

        mtime = path.stat().st_mtime
        if self._cache is not None:
            cached_path, cached_mtime, rows = self._cache
            if cached_path == path and cached_mtime == mtime:
                return rows

        logger.info("Loading restaurant snapshot: %s", path)
        rows = load_restaurants_parquet(path)
        self._cache = (path, mtime, rows)
        return rows

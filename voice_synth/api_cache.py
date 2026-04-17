"""Small persistent caches for provider metadata API calls.

This module is intentionally separate from phrase audio caching: providers use
it for relatively slow and account-scoped metadata such as voice lists and model
lists. Cache keys should include any credential, region, or option that changes
the API response so cached data from one account cannot leak into another.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import math
from pathlib import Path
from typing import TypeVar

from pypercache import Cache

T = TypeVar("T")

# The Azure Speech and ElevenLabs metadata endpoint docs do not publish cache
# expiry guidance. Default to no expiry and rely on explicit invalidation or a
# caller-configured TTL.
AZURE_VOICE_LIST_TTL_SECONDS = math.inf
ELEVENLABS_VOICE_LIST_TTL_SECONDS = math.inf
ELEVENLABS_MODEL_LIST_TTL_SECONDS = math.inf


def build_api_cache_path(base_dir: str | Path, api_name: str) -> Path:
    """Return the JSON cache file path used for one provider's API metadata."""

    return Path(base_dir) / api_name / "cache.json"


def build_scoped_cache_key(base_key: str, *scope_parts: str | None) -> str:
    """Append a short hash of sensitive scope values to a stable cache key.

    The raw scope values may include secrets, so only the digest is stored in
    the cache file while still partitioning entries by credential or region.
    """

    normalized_scope = "|".join((part or "").strip() for part in scope_parts)
    if not normalized_scope:
        return base_key
    scope_hash = hashlib.sha256(normalized_scope.encode("utf-8")).hexdigest()[:16]
    return f"{base_key}:{scope_hash}"


class APICache:
    """Persistent key/value wrapper around ``pypercache`` for provider metadata."""

    def __init__(self, api_name: str, base_dir: str | Path) -> None:
        """Create or open the cache file for one provider namespace."""

        self.api_name = api_name
        self.path = build_api_cache_path(base_dir, api_name)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(str(self.path))

    def get_or_fetch(self, key: str, fetcher: Callable[[], T], *, ttl_seconds: int | float) -> T:
        """Return a fresh cached value, fetching and storing it when absent or stale."""

        if self._cache.has(key):
            record = self._cache.get(key)
            if not record.is_data_stale:
                return record.data

        data = fetcher()
        self._cache.store(key, data, expiry=ttl_seconds)
        return data

    def invalidate(self, key: str | None = None, *, prefix: str | None = None) -> int:
        """Remove exact or prefix-matched entries and return the number deleted."""

        if key is None and prefix is None:
            raise ValueError("Pass key, prefix, or use clear() to erase the whole API cache.")

        records = self._cache.storage.records
        keys = []
        if key is not None and key in records:
            keys.append(key)
        if prefix is not None:
            keys.extend(record_key for record_key in records if record_key.startswith(prefix))

        removed = 0
        for record_key in set(keys):
            if record_key in records:
                del records[record_key]
                removed += 1
        if removed:
            self._cache.storage.save(records)
        return removed

    def clear(self) -> None:
        """Erase all metadata entries in this provider cache."""

        self._cache.completely_erase_cache()

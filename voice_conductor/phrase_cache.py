"""SQLite-backed cache for synthesized phrases."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Literal

import msgpack
import numpy as np

from voice_conductor.types import SynthesizedAudio

CacheLookupMode = Literal["strict", "relaxed"]

_EXPECTED_COLUMNS = {
    "provider",
    "voice_key",
    "text_key",
    "settings_hash",
    "settings_json",
    "payload",
}


@dataclass(slots=True)
class CacheKey:
    """Lookup identity for one synthesized phrase cache entry."""

    text: str
    provider: str
    voice_key: str
    settings_json: str = ""

    @property
    def normalized_text(self) -> str:
        """Case-insensitive phrase key used by the SQLite primary key."""

        return self.text.lower()

    @property
    def settings_hash(self) -> str:
        """Compact hash for provider settings that affect synthesized audio."""

        return hash_settings_json(self.settings_json)


def canonical_settings_json(value: str | dict[str, Any] | None) -> str:
    """Serialize settings in a deterministic shape before hashing."""

    if value is None:
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def hash_settings_json(value: str | dict[str, Any] | None) -> str:
    """Return a short deterministic hash for provider settings JSON."""

    settings_json = canonical_settings_json(value)
    if not settings_json:
        return "default"
    return hashlib.sha256(settings_json.encode("utf-8")).hexdigest()[:16]


class PhraseCache:
    """Persist synthesized audio clips in SQLite for later replay."""

    def __init__(self, path: str | Path) -> None:
        """Open or create the phrase cache database at ``path``."""

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=MEMORY")
        return self._conn

    def close(self) -> None:
        """Close the reusable SQLite connection, if one is open."""

        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __enter__(self) -> PhraseCache:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _discard_connection(self) -> None:
        """Close the current connection before resetting or reopening the DB."""

        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_db(self) -> None:
        with self._lock:
            try:
                conn = self._connect()
            except sqlite3.OperationalError:
                self._reset_database_file()
                conn = self._connect()
            try:
                try:
                    unsupported_schema = self._has_unsupported_schema(conn)
                except sqlite3.OperationalError:
                    self._discard_connection()
                    self._reset_database_file()
                    conn = self._connect()
                    unsupported_schema = False
                if unsupported_schema:
                    try:
                        conn.execute("DROP TABLE phrase_cache")
                    except sqlite3.OperationalError:
                        self._discard_connection()
                        self._reset_database_file()
                        conn = self._connect()
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS phrase_cache (
                        provider TEXT NOT NULL,
                        voice_key TEXT NOT NULL,
                        text_key TEXT NOT NULL,
                        settings_hash TEXT NOT NULL,
                        settings_json TEXT NOT NULL,
                        payload BLOB NOT NULL,
                        PRIMARY KEY (provider, voice_key, text_key, settings_hash)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_phrase_cache_relaxed
                    ON phrase_cache (provider, voice_key, text_key)
                    """
                )
                conn.commit()
            except Exception:
                self._discard_connection()
                raise
            finally:
                self._discard_connection()

    def _reset_database_file(self) -> None:
        """Delete an unsupported cache DB and sidecar payload files."""

        self._discard_connection()
        try:
            self.path.unlink(missing_ok=True)
            self.path.with_name(f"{self.path.name}-journal").unlink(missing_ok=True)
            for sidecar in self.path.parent.glob(f"{self.path.name}-x-*"):
                sidecar.unlink(missing_ok=True)
        except PermissionError:
            original = self.path
            for version in range(2, 10):
                candidate = original.with_name(f"{original.stem}.v{version}{original.suffix}")
                try:
                    candidate.unlink(missing_ok=True)
                    candidate.with_name(f"{candidate.name}-journal").unlink(missing_ok=True)
                except PermissionError:
                    continue
                self.path = candidate
                for sidecar in self.path.parent.glob(f"{self.path.name}-x-*"):
                    sidecar.unlink(missing_ok=True)
                return
            raise

    def _has_unsupported_schema(self, conn: sqlite3.Connection) -> bool:
        exists = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'phrase_cache'
            """
        ).fetchone()
        if exists is None:
            return False
        columns = {row[1] for row in conn.execute("PRAGMA table_info(phrase_cache)").fetchall()}
        return columns != _EXPECTED_COLUMNS

    def get(
        self,
        key: CacheKey,
        *,
        lookup_mode: CacheLookupMode = "strict",
    ) -> SynthesizedAudio | None:
        """Return cached audio for ``key`` when present."""

        if lookup_mode not in {"strict", "relaxed"}:
            raise ValueError("lookup_mode must be 'strict' or 'relaxed'.")

        with self._lock:
            conn = self._connect()
            if lookup_mode == "strict":
                row = conn.execute(
                    """
                    SELECT payload
                    FROM phrase_cache
                    WHERE provider = ? AND voice_key = ? AND text_key = ? AND settings_hash = ?
                    """,
                    (key.provider, key.voice_key, key.normalized_text, key.settings_hash),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT payload
                    FROM phrase_cache
                    WHERE provider = ? AND voice_key = ? AND text_key = ?
                    ORDER BY CASE WHEN settings_hash = ? THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (key.provider, key.voice_key, key.normalized_text, key.settings_hash),
                ).fetchone()
        if row is None:
            return None
        return self._deserialize(row[0])

    def set(self, key: CacheKey, audio: SynthesizedAudio) -> None:
        """Insert or replace a synthesized phrase payload."""

        payload = self._serialize(audio)
        with self._lock:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO phrase_cache (
                    provider,
                    voice_key,
                    text_key,
                    settings_hash,
                    settings_json,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, voice_key, text_key, settings_hash)
                DO UPDATE SET
                    settings_json = excluded.settings_json,
                    payload = excluded.payload
                """,
                (
                    key.provider,
                    key.voice_key,
                    key.normalized_text,
                    key.settings_hash,
                    canonical_settings_json(key.settings_json),
                    payload,
                ),
            )
            conn.commit()

    def invalidate(
        self,
        key: CacheKey | None = None,
        *,
        text: str | None = None,
        provider: str | None = None,
        voice_key: str | None = None,
    ) -> int:
        """Delete matching entries and return the number of rows removed."""

        if key is not None:
            text = key.text
            provider = key.provider
            voice_key = key.voice_key
        filters: list[str] = []
        params: list[str] = []
        if text is not None:
            filters.append("text_key = ?")
            params.append(text.lower())
        if provider is not None:
            filters.append("provider = ?")
            params.append(provider)
        if voice_key is not None:
            filters.append("voice_key = ?")
            params.append(voice_key)
        if not filters:
            raise ValueError("Pass a cache key or at least one filter, or use clear().")

        with self._lock:
            conn = self._connect()
            cursor = conn.execute(
                f"DELETE FROM phrase_cache WHERE {' AND '.join(filters)}",
                tuple(params),
            )
            conn.commit()
            return int(cursor.rowcount)

    def clear(self) -> None:
        """Remove all phrase cache rows without deleting the database file."""

        with self._lock:
            conn = self._connect()
            conn.execute("DELETE FROM phrase_cache")
            conn.commit()

    def _serialize(self, audio: SynthesizedAudio) -> bytes:
        """Pack audio samples and metadata into a msgpack BLOB."""

        packed = {
            "samples": np.asarray(audio.samples, dtype=np.float32).tobytes(),
            "shape": list(audio.samples.shape),
            "sample_rate": audio.sample_rate,
            "channels": audio.channels,
            "provider": audio.provider,
            "voice": audio.voice,
            "text": audio.text,
            "metadata": audio.metadata,
        }
        return msgpack.packb(packed, use_bin_type=True)

    def _deserialize(self, payload: bytes) -> SynthesizedAudio:
        """Restore a ``SynthesizedAudio`` object from a msgpack BLOB."""

        unpacked: dict[str, Any] = msgpack.unpackb(payload, raw=False)
        shape = tuple(unpacked["shape"])
        samples = np.frombuffer(unpacked["samples"], dtype=np.float32).reshape(shape)
        return SynthesizedAudio(
            samples=samples.copy(),
            sample_rate=int(unpacked["sample_rate"]),
            channels=int(unpacked["channels"]),
            provider=str(unpacked["provider"]),
            voice=unpacked.get("voice"),
            text=unpacked.get("text"),
            metadata=dict(unpacked.get("metadata") or {}),
        )

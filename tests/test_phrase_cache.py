from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest

import numpy as np

from voice_conductor.phrase_cache import CacheKey, PhraseCache
from voice_conductor.types import SynthesizedAudio


def _audio(text: str = "hello") -> SynthesizedAudio:
    return SynthesizedAudio(
        samples=np.zeros((8, 1), dtype=np.float32),
        sample_rate=16000,
        channels=1,
        provider="kokoro",
        voice="af_heart",
        text=text,
    )


class PhraseCacheTests(unittest.TestCase):
    def test_strict_lookup_requires_matching_settings_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with PhraseCache(Path(temp_dir) / "phrases.db") as cache:
                first = CacheKey(
                    text="Need backup",
                    provider="kokoro",
                    voice_key="kokoro:af_heart",
                    settings_json='{"speed":1.0}',
                )
                second = CacheKey(
                    text="Need backup",
                    provider="kokoro",
                    voice_key="kokoro:af_heart",
                    settings_json='{"speed":1.5}',
                )

                cache.set(first, _audio("Need backup"))

                self.assertIsNotNone(cache.get(first))
                self.assertIsNone(cache.get(second))

    def test_relaxed_lookup_ignores_settings_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with PhraseCache(Path(temp_dir) / "phrases.db") as cache:
                cached_key = CacheKey(
                    text="Need backup",
                    provider="kokoro",
                    voice_key="kokoro:af_heart",
                    settings_json='{"speed":1.0}',
                )
                relaxed_key = CacheKey(
                    text="need backup",
                    provider="kokoro",
                    voice_key="kokoro:af_heart",
                    settings_json='{"speed":1.5}',
                )

                cache.set(cached_key, _audio("Need backup"))

                self.assertIsNotNone(cache.get(relaxed_key, lookup_mode="relaxed"))

    def test_reuses_cache_after_close_reopens_connection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with PhraseCache(Path(temp_dir) / "phrases.db") as cache:
                key = CacheKey(
                    text="Need backup",
                    provider="kokoro",
                    voice_key="kokoro:af_heart",
                )

                cache.set(key, _audio("Need backup"))
                cache.close()
                cache.close()

                cached = cache.get(key)

        self.assertIsNotNone(cached)
        self.assertEqual(cached.text, "Need backup")

    def test_invalid_lookup_mode_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with PhraseCache(Path(temp_dir) / "phrases.db") as cache:
                key = CacheKey(
                    text="Need backup",
                    provider="kokoro",
                    voice_key="kokoro:af_heart",
                )

                with self.assertRaisesRegex(ValueError, "lookup_mode"):
                    cache.get(key, lookup_mode="loose")  # type: ignore[arg-type]

    def test_single_cache_instance_supports_threaded_reads_and_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with PhraseCache(Path(temp_dir) / "phrases.db") as cache:

                def cache_round_trip(index: int) -> str | None:
                    key = CacheKey(
                        text=f"Need backup {index}",
                        provider="kokoro",
                        voice_key="kokoro:af_heart",
                    )
                    cache.set(key, _audio(key.text))
                    cached = cache.get(key)
                    return cached.text if cached is not None else None

                with ThreadPoolExecutor(max_workers=4) as executor:
                    results = list(executor.map(cache_round_trip, range(20)))

        self.assertEqual(results, [f"Need backup {index}" for index in range(20)])

    def test_unsupported_schema_is_reset_without_legacy_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "phrases.db"
            conn = sqlite3.connect(path)
            try:
                conn.execute(
                    """
                    CREATE TABLE phrase_cache (
                        provider TEXT NOT NULL,
                        voice TEXT NOT NULL,
                        text_key TEXT NOT NULL,
                        payload BLOB NOT NULL,
                        PRIMARY KEY (provider, voice, text_key)
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

            with PhraseCache(path):
                pass

            conn = sqlite3.connect(path)
            try:
                columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(phrase_cache)").fetchall()
                }
            finally:
                conn.close()

        self.assertEqual(
            columns,
            {"provider", "voice_key", "text_key", "settings_hash", "settings_json", "payload"},
        )

    def test_cache_operates_after_schema_reset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "phrases.db"
            conn = sqlite3.connect(path)
            try:
                conn.execute(
                    """
                    CREATE TABLE phrase_cache (
                        provider TEXT NOT NULL,
                        voice TEXT NOT NULL,
                        text_key TEXT NOT NULL,
                        payload BLOB NOT NULL,
                        PRIMARY KEY (provider, voice, text_key)
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

            with PhraseCache(path) as cache:
                key = CacheKey(
                    text="Need backup",
                    provider="kokoro",
                    voice_key="kokoro:af_heart",
                )
                cache.set(key, _audio("Need backup"))

                cached = cache.get(key)

        self.assertIsNotNone(cached)
        self.assertEqual(cached.text, "Need backup")


if __name__ == "__main__":
    unittest.main()

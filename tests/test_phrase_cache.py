from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

import numpy as np

from voice_synth.phrase_cache import CacheKey, PhraseCache
from voice_synth.types import SynthesizedAudio


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
            cache = PhraseCache(Path(temp_dir) / "phrases.db")
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
            cache = PhraseCache(Path(temp_dir) / "phrases.db")
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

            PhraseCache(path)

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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import math
import os
import tempfile
import unittest

from voice_synth.api_cache import APICache
from voice_synth.api_cache import AZURE_VOICE_LIST_TTL_SECONDS
from voice_synth.api_cache import ELEVENLABS_MODEL_LIST_TTL_SECONDS
from voice_synth.api_cache import ELEVENLABS_VOICE_LIST_TTL_SECONDS
from voice_synth.api_cache import build_api_cache_path
from voice_synth.api_cache import build_scoped_cache_key
from voice_synth.config import _default_cache_path
from voice_synth.config import _default_api_cache_dir
from voice_synth.config import load_settings


class APICacheTests(unittest.TestCase):
    def test_default_cache_paths_are_cwd_local(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            os.chdir(temp_path)
            try:
                default_cache_path = Path(_default_cache_path())
                default_api_dir = Path(_default_api_cache_dir())
            finally:
                os.chdir(original_cwd)

        self.assertEqual(default_cache_path, temp_path / "voice_synth_cache.db")
        self.assertEqual(default_api_dir, temp_path / "api-caches")

    def test_default_cache_paths_can_be_derived_from_custom_root(self) -> None:
        root = Path("runtime-cache")

        self.assertEqual(Path(_default_cache_path(root)), root / "voice_synth_cache.db")
        self.assertEqual(Path(_default_api_cache_dir(root)), root / "api-caches")

    def test_build_api_cache_path_uses_api_name_subdirectory(self) -> None:
        path = build_api_cache_path("cache-root", "elevenlabs")
        self.assertEqual(path, Path("cache-root") / "elevenlabs" / "cache.json")

    def test_build_scoped_cache_key_hashes_scope_without_exposing_raw_values(self) -> None:
        key = build_scoped_cache_key("voices:list", "region-a", "secret-key")
        self.assertTrue(key.startswith("voices:list:"))
        self.assertNotIn("region-a", key)
        self.assertNotIn("secret-key", key)

    def test_get_or_fetch_reuses_fresh_cached_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = APICache("azure", temp_dir)
            calls = 0

            def fetch():
                nonlocal calls
                calls += 1
                return {"voices": ["Ava"]}

            first = cache.get_or_fetch("voices:list", fetch, ttl_seconds=60)
            second = cache.get_or_fetch("voices:list", fetch, ttl_seconds=60)

        self.assertEqual(first, {"voices": ["Ava"]})
        self.assertEqual(second, {"voices": ["Ava"]})
        self.assertEqual(calls, 1)

    def test_get_or_fetch_refreshes_stale_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = APICache("elevenlabs", temp_dir)
            calls = 0

            def fetch():
                nonlocal calls
                calls += 1
                return {"call": calls}

            cache.get_or_fetch("voices:list", fetch, ttl_seconds=-1)
            refreshed = cache.get_or_fetch("voices:list", fetch, ttl_seconds=60)

        self.assertEqual(refreshed, {"call": 2})
        self.assertEqual(calls, 2)

    def test_provider_metadata_cache_ttls_default_to_no_expiry(self) -> None:
        self.assertTrue(math.isinf(AZURE_VOICE_LIST_TTL_SECONDS))
        self.assertTrue(math.isinf(ELEVENLABS_VOICE_LIST_TTL_SECONDS))
        self.assertTrue(math.isinf(ELEVENLABS_MODEL_LIST_TTL_SECONDS))

    def test_invalidate_removes_key_and_prefix_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = APICache("elevenlabs", temp_dir)
            cache.get_or_fetch("voices:list:one", lambda: {"voice": 1}, ttl_seconds=math.inf)
            cache.get_or_fetch("voices:list:two", lambda: {"voice": 2}, ttl_seconds=math.inf)
            cache.get_or_fetch("models:list", lambda: {"model": 1}, ttl_seconds=math.inf)

            removed = cache.invalidate(prefix="voices:list")
            cached_model = cache.get_or_fetch("models:list", lambda: {"model": 2}, ttl_seconds=math.inf)

        self.assertEqual(removed, 2)
        self.assertEqual(cached_model, {"model": 1})

    def test_load_settings_reads_api_cache_settings_from_json(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "voice_synth.config.json").write_text(
                '{"voice_synth":{"cache":{"api_dir":"custom-api-cache","ttl_seconds":"900"}}}',
                encoding="utf-8",
            )
            os.chdir(temp_path)
            try:
                settings = load_settings()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(settings.voice_synth.cache.api_dir, str(temp_path / "custom-api-cache"))
        self.assertEqual(settings.voice_synth.cache.ttl_seconds, 900)

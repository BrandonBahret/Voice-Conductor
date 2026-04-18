from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from voice_conductor import (
    CacheSettings,
    DemoProvider,
    DemoProviderSettings,
    ProviderSettings,
    Settings,
    TTSManager,
    VoiceConductorSettings,
    settings_from_dict,
    settings_to_dict,
)


class DemoProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = DemoProvider(Settings())

    def test_synthesize_is_deterministic_for_the_same_input(self) -> None:
        text = "Welcome aboard, commander."

        first = self.provider.synthesize(text, voice="demo:animalese")
        second = self.provider.synthesize(text, voice="demo:animalese")

        np.testing.assert_allclose(first.samples, second.samples, rtol=0.0, atol=0.0)
        self.assertEqual(first.metadata, second.metadata)
        self.assertEqual(first.duration_seconds, second.duration_seconds)

    def test_synthesize_accepts_short_voice_names_but_records_canonical_id(self) -> None:
        audio = self.provider.synthesize("short names are nicer", voice="robot")

        self.assertEqual(audio.voice, "demo:robot")
        self.assertEqual(audio.metadata["normalized_voice_key"], "demo:robot")

    def test_default_voice_accepts_short_voice_name(self) -> None:
        provider = DemoProvider(
            Settings(
                providers=ProviderSettings(
                    demo=DemoProviderSettings(default_voice="robot"),
                )
            )
        )

        self.assertEqual(provider.default_voice(), "demo:robot")

    def test_synthesize_records_monotonic_word_timing(self) -> None:
        text = (
            "Welcome aboard, commander. This is your ship's computer speaking. "
            "Let's test the voice conductoresis system with this phrase."
        )

        audio = self.provider.synthesize(text, voice="demo:animalese")
        word_timing = audio.metadata.get("word_timing")

        self.assertIsInstance(word_timing, list)
        self.assertEqual([item["text"] for item in word_timing], text.split())
        self.assertGreater(len(word_timing), 0)

        previous_start = -1.0
        for index, item in enumerate(word_timing):
            start_seconds = float(item["start_seconds"])
            end_seconds = float(item["end_seconds"])
            self.assertGreaterEqual(start_seconds, 0.0)
            self.assertGreaterEqual(start_seconds, previous_start)
            self.assertGreaterEqual(end_seconds, start_seconds)
            if index + 1 < len(word_timing):
                next_start = float(word_timing[index + 1]["start_seconds"])
                self.assertAlmostEqual(end_seconds, next_start, places=6)
            previous_start = start_seconds

        self.assertLessEqual(float(word_timing[-1]["end_seconds"]), audio.duration_seconds + 1e-6)
        self.assertAlmostEqual(float(word_timing[-1]["end_seconds"]), audio.duration_seconds, places=6)

    def test_sentence_punctuation_lingers_longer_than_mid_sentence_punctuation(self) -> None:
        comma_audio = self.provider.synthesize("Alpha, beta", voice="demo:pilot")
        period_audio = self.provider.synthesize("Alpha. beta", voice="demo:pilot")

        comma_word_timing = comma_audio.metadata["word_timing"]
        period_word_timing = period_audio.metadata["word_timing"]

        comma_gap = float(comma_word_timing[0]["end_seconds"]) - float(comma_word_timing[0]["start_seconds"])
        period_gap = float(period_word_timing[0]["end_seconds"]) - float(period_word_timing[0]["start_seconds"])

        self.assertGreater(period_gap, comma_gap)
        self.assertGreater(period_audio.duration_seconds, comma_audio.duration_seconds)

    def test_multisyllable_words_render_in_chunked_audio_regions(self) -> None:
        word = "banana"

        syllable_chunks = self.provider._split_syllable_chunks(word)
        audio = self.provider.synthesize(word, voice="demo:robot")
        samples = audio.samples[:, 0]

        silence_mask = np.isclose(samples, 0.0, atol=1e-8)
        region_lengths: list[int] = []
        region_start = 0
        cursor = 0
        while cursor < len(silence_mask):
            if silence_mask[cursor]:
                silence_end = cursor
                while silence_end < len(silence_mask) and silence_mask[silence_end]:
                    silence_end += 1
                if silence_end - cursor >= 20 and cursor > region_start:
                    region_lengths.append(cursor - region_start)
                    region_start = silence_end
                cursor = silence_end
                continue
            cursor += 1
        if region_start < len(samples):
            region_lengths.append(len(samples) - region_start)

        self.assertGreater(len(syllable_chunks), 1)
        self.assertEqual(len(region_lengths), len(syllable_chunks))
        self.assertGreater(len(set(region_lengths)), 1)

    def test_settings_round_trip_demo_config(self) -> None:
        settings = settings_from_dict(
            {
                "providers": {
                    "demo": {
                        "default_voice": "demo:robot",
                        "speed": 1.35,
                    }
                }
            }
        )

        demo_settings = settings.provider_settings("demo")
        payload = settings_to_dict(settings)

        self.assertIsInstance(demo_settings, DemoProviderSettings)
        self.assertEqual(demo_settings.default_voice, "robot")
        self.assertEqual(demo_settings.speed, 1.35)
        self.assertEqual(payload["providers"]["demo"]["default_voice"], "robot")
        self.assertEqual(payload["providers"]["demo"]["speed"], 1.35)

    def test_manager_can_use_registered_builtin_demo_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                voice_conductor=VoiceConductorSettings(
                    provider_chain=["demo"],
                    cache=CacheSettings(path=str(Path(temp_dir) / "voice_conductor_cache.db")),
                ),
                providers=ProviderSettings(
                    demo=DemoProviderSettings(default_voice="robot", speed=1.2),
                ),
            )
            manager = TTSManager(settings=settings)
            audio = manager.synthesize("hello from the demo provider")
            manager.close()

        self.assertEqual(audio.provider, "demo")
        self.assertEqual(audio.voice, "demo:robot")
        self.assertEqual(audio.metadata["demo"], True)


if __name__ == "__main__":
    unittest.main()

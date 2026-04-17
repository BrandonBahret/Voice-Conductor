from __future__ import annotations

import unittest

from voice_synth.voice_keys import normalize_voice_config_value, normalize_voice_key


class VoiceKeyTests(unittest.TestCase):
    def test_normalizes_windows_voice_names(self) -> None:
        self.assertEqual(
            normalize_voice_key("windows", "Microsoft David Desktop"),
            "windows:david",
        )

    def test_normalizes_kokoro_voice_ids(self) -> None:
        self.assertEqual(normalize_voice_key("kokoro", "af_heart"), "kokoro:af_heart")

    def test_elevenlabs_keeps_stable_voice_id(self) -> None:
        self.assertEqual(
            normalize_voice_key("elevenlabs", "CwhRBWXzGAHq8TQ4Fs17"),
            "elevenlabs:CwhRBWXzGAHq8TQ4Fs17",
        )

    def test_normalizes_provider_local_config_values(self) -> None:
        self.assertEqual(
            normalize_voice_config_value("windows", "Microsoft David Desktop"),
            "david",
        )
        self.assertEqual(
            normalize_voice_config_value("demo", "demo:animalese"),
            "animalese",
        )
        self.assertEqual(
            normalize_voice_config_value("elevenlabs", "JBFqnCBsd6RMkjVDRZzb"),
            "JBFqnCBsd6RMkjVDRZzb",
        )


if __name__ == "__main__":
    unittest.main()

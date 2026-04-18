from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np

from voice_conductor.types import SynthesizedAudio


class SynthesizedAudioTests(unittest.TestCase):
    def test_to_wav_bytes_exports_inspectable_wav(self) -> None:
        audio = SynthesizedAudio(
            samples=np.zeros((160, 1), dtype=np.float32),
            sample_rate=16000,
            channels=1,
            provider="test",
        )

        wav_bytes = audio.to_wav_bytes()

        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        with tempfile.TemporaryDirectory() as temp_dir:
            path = audio.copy_to(Path(temp_dir) / "voice.wav")
            with wave.open(str(path), "rb") as wav_file:
                self.assertEqual(wav_file.getnchannels(), 1)
                self.assertEqual(wav_file.getframerate(), 16000)
                self.assertEqual(wav_file.getnframes(), 160)

    def test_to_pcm16_bytes_exports_raw_audio(self) -> None:
        audio = SynthesizedAudio(
            samples=np.array([[-1.0], [0.0], [1.0]], dtype=np.float32),
            sample_rate=16000,
            channels=1,
            provider="test",
        )

        pcm = audio.to_pcm16_bytes()

        self.assertEqual(len(pcm), 6)

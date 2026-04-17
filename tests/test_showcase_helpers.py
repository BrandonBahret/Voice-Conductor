from __future__ import annotations

from html import escape
import unittest

from voice_synth import DemoProvider, Settings
from voice_synth._showcase_helpers import build_word_timing_transcript_html


class ShowcaseHelperTests(unittest.TestCase):
    def test_build_word_timing_transcript_html_emits_timed_word_spans(self) -> None:
        text = "Welcome aboard, commander."

        audio = DemoProvider(Settings()).synthesize(text, voice="demo:animalese")
        word_timing = audio.metadata["word_timing"]
        html = build_word_timing_transcript_html(audio, label="Demo word sync")

        self.assertIn("Demo word sync", html)
        self.assertEqual(html.count('class="voice-synth-word"'), len(word_timing))

        for item in word_timing:
            self.assertIn(f'data-start="{float(item["start_seconds"]):.6f}"', html)
            self.assertIn(f'data-end="{float(item["end_seconds"]):.6f}"', html)
            self.assertIn(escape(str(item["text"])), html)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_synth.config import settings_from_dict
from voice_synth.exceptions import ConfigurationError, DependencyError
from voice_synth.providers.kokoro import KokoroProvider


class KokoroProviderTests(unittest.TestCase):
    def test_list_voices_can_be_called_without_instantiating_provider(self) -> None:
        voices = KokoroProvider.list_voices()

        self.assertEqual(voices[0].id, "af_heart")
        self.assertEqual(voices[0].provider, "kokoro")

    def test_is_available_requires_kokoro_package_and_hf_token(self) -> None:
        provider = KokoroProvider(
            settings_from_dict({"providers": {"kokoro": {"hf_token": "hf-test-token"}}})
        )

        with patch("importlib.util.find_spec", return_value=object()):
            self.assertTrue(provider.is_available())

    def test_is_available_is_false_without_hf_token(self) -> None:
        provider = KokoroProvider(settings_from_dict({}))

        with patch("importlib.util.find_spec", return_value=object()):
            self.assertFalse(provider.is_available())

    def test_is_available_is_false_with_blank_hf_token(self) -> None:
        provider = KokoroProvider(
            settings_from_dict({"providers": {"kokoro": {"hf_token": "   "}}})
        )

        with patch("importlib.util.find_spec", return_value=object()):
            self.assertFalse(provider.is_available())

    def test_is_available_is_false_without_kokoro_package(self) -> None:
        provider = KokoroProvider(
            settings_from_dict({"providers": {"kokoro": {"hf_token": "hf-test-token"}}})
        )

        with patch("importlib.util.find_spec", return_value=None):
            self.assertFalse(provider.is_available())

    def test_ensure_pipeline_reports_missing_hf_token_as_config_error(self) -> None:
        provider = KokoroProvider(settings_from_dict({}))

        with patch("importlib.util.find_spec", return_value=object()):
            with self.assertRaisesRegex(
                ConfigurationError,
                "Kokoro requires providers.kokoro.hf_token.",
            ):
                provider._ensure_pipeline()

    def test_ensure_pipeline_reports_missing_package_as_dependency_error(self) -> None:
        provider = KokoroProvider(
            settings_from_dict({"providers": {"kokoro": {"hf_token": "hf-test-token"}}})
        )

        with patch("importlib.util.find_spec", return_value=None):
            with self.assertRaisesRegex(
                DependencyError,
                re.escape(
                    "Kokoro backend requires the optional 'kokoro' package. "
                    "Install it with 'pip install \"voice-synth[kokoro]\"'."
                ),
            ):
                provider._ensure_pipeline()

    def test_configured_hf_token_logs_in(self) -> None:
        provider = KokoroProvider(
            settings_from_dict({"providers": {"kokoro": {"hf_token": "hf-test-token"}}})
        )

        with patch("huggingface_hub.login") as mock_login:
            provider._configure_huggingface_token()

            mock_login.assert_called_once_with(
                token="hf-test-token",
                add_to_git_credential=False,
                skip_if_logged_in=True,
            )

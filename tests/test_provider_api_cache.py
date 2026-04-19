from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from voice_conductor.config import Settings, settings_from_dict
from voice_conductor.providers.azure import AzureSpeechProvider
from voice_conductor.providers.elevenlabs import ElevenLabsProvider


class _FakeHTTPResponse:
    def __init__(self, payload: object) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _BinaryHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_BinaryHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _settings(
    *,
    cache_dir: str,
    elevenlabs: dict[str, object] | None = None,
    azure: dict[str, object] | None = None,
    ttl_seconds: int | None = None,
) -> Settings:
    cache: dict[str, object] = {"api_dir": cache_dir}
    if ttl_seconds is not None:
        cache["ttl_seconds"] = ttl_seconds
    payload: dict[str, object] = {
        "voice_conductor": {
            "cache": cache,
        },
        "providers": {},
    }
    providers = payload["providers"]
    assert isinstance(providers, dict)
    if elevenlabs is not None:
        providers["elevenlabs"] = elevenlabs
    if azure is not None:
        providers["azure"] = azure
    return settings_from_dict(payload)


class ProviderAPICacheTests(unittest.TestCase):
    def test_elevenlabs_voice_list_uses_disk_cache_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = _settings(cache_dir=temp_dir, elevenlabs={"api_key": "test-key"})
            payload = {
                "voices": [
                    {"voice_id": "voice-1", "name": "Rachel", "category": "generated"}
                ]
            }
            with patch("voice_conductor.providers.elevenlabs.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value = _FakeHTTPResponse(payload)
                first = ElevenLabsProvider(settings).list_voices()
                second = ElevenLabsProvider(settings).list_voices()

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].id, "voice-1")
        self.assertEqual(len(second), 1)
        self.assertEqual(mock_urlopen.call_count, 1)

    def test_azure_voice_list_uses_disk_cache_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = _settings(
                cache_dir=temp_dir,
                azure={"speech_key": "test-key", "region": "westus"},
            )
            payload = [
                {
                    "ShortName": "en-US-AvaNeural",
                    "DisplayName": "Ava",
                    "Locale": "en-US",
                    "Gender": "Female",
                    "LocalName": "Ava",
                }
            ]
            with patch("voice_conductor.providers.azure.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value = _FakeHTTPResponse(payload)
                first = AzureSpeechProvider(settings).list_voices()
                second = AzureSpeechProvider(settings).list_voices()

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].id, "en-US-AvaNeural")
        self.assertEqual(first[0].language, "en-US")
        self.assertEqual(len(second), 1)
        self.assertEqual(mock_urlopen.call_count, 1)

    def test_elevenlabs_voice_cache_is_scoped_per_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_settings = _settings(cache_dir=temp_dir, elevenlabs={"api_key": "test-key-1"})
            second_settings = _settings(cache_dir=temp_dir, elevenlabs={"api_key": "test-key-2"})
            first_payload = {
                "voices": [
                    {"voice_id": "voice-1", "name": "Rachel", "category": "generated"}
                ]
            }
            second_payload = {
                "voices": [
                    {"voice_id": "voice-2", "name": "Adam", "category": "generated"}
                ]
            }
            with patch("voice_conductor.providers.elevenlabs.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = [
                    _FakeHTTPResponse(first_payload),
                    _FakeHTTPResponse(second_payload),
                ]
                first = ElevenLabsProvider(first_settings).list_voices()
                second = ElevenLabsProvider(second_settings).list_voices()

        self.assertEqual(first[0].id, "voice-1")
        self.assertEqual(second[0].id, "voice-2")
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_azure_voice_cache_is_scoped_per_region_and_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_settings = _settings(
                cache_dir=temp_dir,
                azure={"speech_key": "test-key-1", "region": "westus"},
            )
            second_settings = _settings(
                cache_dir=temp_dir,
                azure={"speech_key": "test-key-2", "region": "eastus"},
            )
            first_payload = [
                {
                    "ShortName": "en-US-AvaNeural",
                    "DisplayName": "Ava",
                    "Locale": "en-US",
                    "Gender": "Female",
                    "LocalName": "Ava",
                }
            ]
            second_payload = [
                {
                    "ShortName": "en-US-JennyNeural",
                    "DisplayName": "Jenny",
                    "Locale": "en-US",
                    "Gender": "Female",
                    "LocalName": "Jenny",
                }
            ]
            with patch("voice_conductor.providers.azure.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = [
                    _FakeHTTPResponse(first_payload),
                    _FakeHTTPResponse(second_payload),
                ]
                first = AzureSpeechProvider(first_settings).list_voices()
                second = AzureSpeechProvider(second_settings).list_voices()

        self.assertEqual(first[0].id, "en-US-AvaNeural")
        self.assertEqual(first[0].language, "en-US")
        self.assertEqual(second[0].id, "en-US-JennyNeural")
        self.assertEqual(second[0].language, "en-US")
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_provider_cache_ttl_zero_does_not_fall_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = _settings(
                cache_dir=temp_dir,
                elevenlabs={"api_key": "test-key"},
                ttl_seconds=0,
            )
            first_payload = {
                "voices": [
                    {"voice_id": "voice-1", "name": "Rachel", "category": "generated"}
                ]
            }
            second_payload = {
                "voices": [
                    {"voice_id": "voice-2", "name": "Adam", "category": "generated"}
                ]
            }
            with patch("voice_conductor.providers.elevenlabs.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = [
                    _FakeHTTPResponse(first_payload),
                    _FakeHTTPResponse(second_payload),
                ]
                first = ElevenLabsProvider(settings).list_voices()
                second = ElevenLabsProvider(settings).list_voices()

        self.assertEqual(first[0].id, "voice-1")
        self.assertEqual(second[0].id, "voice-2")
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_elevenlabs_synthesis_applies_provider_voice_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = _settings(
                cache_dir=temp_dir,
                elevenlabs={
                    "api_key": "test-key",
                    "model_id": "eleven_multilingual_v2",
                    "output_format": "pcm_24000",
                    "speed": 1.1,
                    "language_code": "en",
                    "stability": 0.35,
                    "similarity_boost": 0.8,
                    "style": 0.2,
                    "speaker_boost": True,
                },
            )
            provider = ElevenLabsProvider(settings)
            payload = {"voices": [{"voice_id": "voice-1", "name": "Rachel", "category": "generated"}]}
            captured: list[object] = []

            def fake_urlopen(req, timeout=30):
                captured.append(req)
                if len(captured) == 1:
                    return _FakeHTTPResponse(payload)
                return _BinaryHTTPResponse(b"\x00\x00")

            with patch("voice_conductor.providers.elevenlabs.request.urlopen", side_effect=fake_urlopen):
                provider.synthesize("hello", voice="Rachel")

        request_obj = captured[-1]
        self.assertIn("output_format=pcm_24000", request_obj.full_url)
        body = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual(body["model_id"], "eleven_multilingual_v2")
        self.assertEqual(body["language_code"], "en")
        self.assertEqual(body["voice_settings"]["speed"], 1.1)
        self.assertEqual(body["voice_settings"]["stability"], 0.35)
        self.assertEqual(body["voice_settings"]["similarity_boost"], 0.8)
        self.assertEqual(body["voice_settings"]["style"], 0.2)
        self.assertTrue(body["voice_settings"]["use_speaker_boost"])

    def test_azure_synthesis_applies_provider_speed_to_ssml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = _settings(
                cache_dir=temp_dir,
                azure={
                    "speech_key": "test-key",
                    "region": "westus",
                    "speed": 1.25,
                    "language_code": "en-US",
                },
            )
            provider = AzureSpeechProvider(settings)
            captured: list[object] = []

            def fake_urlopen(req, timeout=30):
                captured.append(req)
                return _BinaryHTTPResponse(
                    (
                        b"RIFF(\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                        b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x04\x00\x00\x00"
                        b"\x00\x00\x00\x00"
                    )
                )

            with patch("voice_conductor.providers.azure.request.urlopen", side_effect=fake_urlopen):
                provider.synthesize("hello", voice="en-US-AvaNeural")

        request_obj = captured[-1]
        body = request_obj.data.decode("utf-8")
        self.assertIn("xml:lang='en-US'", body)
        self.assertIn("<prosody rate='1.25'>hello</prosody>", body)

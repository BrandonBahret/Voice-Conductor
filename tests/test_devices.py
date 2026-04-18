from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from voice_conductor.audio.devices import find_output_device, list_output_devices
from voice_conductor.exceptions import DeviceResolutionError


class FakeSoundDevice:
    def __init__(self) -> None:
        self.default = type("Default", (), {"device": [0, 1]})()

    @staticmethod
    def query_devices():
        return [
            {
                "name": "Microphone",
                "hostapi": 0,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
            {
                "name": "Realtek Speakers",
                "hostapi": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
            {
                "name": "CABLE Input (VB-Audio Virtual Cable)",
                "hostapi": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
            {
                "name": "VoiceMeeter Aux Input (VB-Audio VoiceMeeter AUX VAIO)",
                "hostapi": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
        ]

    @staticmethod
    def query_hostapis():
        return [{"name": "Windows WASAPI"}]


class DuplicateWindowsSpeakerSoundDevice:
    def __init__(self) -> None:
        self.default = type("Default", (), {"device": [None, 1]})()

    @staticmethod
    def query_devices():
        return [
            {
                "name": "Speakers (High Definition Audio",
                "hostapi": 0,
                "max_output_channels": 2,
                "default_samplerate": 44100,
            },
            {
                "name": "Speakers (High Definition Audio Device)",
                "hostapi": 1,
                "max_output_channels": 2,
                "default_samplerate": 44100,
            },
            {
                "name": "Speakers (High Definition Audio Device)",
                "hostapi": 2,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
        ]

    @staticmethod
    def query_hostapis():
        return [
            {"name": "MME"},
            {"name": "Windows DirectSound"},
            {"name": "Windows WASAPI"},
        ]


class DeviceTests(unittest.TestCase):
    def _list_output_devices(self, sd) -> list:
        with patch("voice_conductor.audio.devices._load_sounddevice", return_value=sd):
            return list_output_devices()

    def test_list_output_devices_marks_virtual_cable(self) -> None:
        devices = self._list_output_devices(FakeSoundDevice())

        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0].name, "Realtek Speakers")
        self.assertEqual(devices[0].hostapi_name, "Windows WASAPI")
        self.assertEqual(devices[0].host_api, "Windows WASAPI")
        self.assertTrue(devices[0].is_default)
        self.assertTrue(devices[1].is_virtual_cable)
        self.assertTrue(devices[2].is_virtual_cable)

    def test_find_output_device_defaults_to_virtual_cable_when_requested(self) -> None:
        devices = self._list_output_devices(FakeSoundDevice())

        device = find_output_device(devices=devices, prefer_virtual_cable=True)

        self.assertIn("VoiceMeeter Aux Input", device.name)

    def test_find_output_device_matches_normalized_virtual_cable_name(self) -> None:
        devices = self._list_output_devices(FakeSoundDevice())

        device = find_output_device("cable-input", devices=devices)

        self.assertIn("CABLE Input", device.name)

    def test_find_output_device_prefers_mme_for_duplicate_speaker_names(self) -> None:
        devices = self._list_output_devices(DuplicateWindowsSpeakerSoundDevice())

        device = find_output_device("Speakers (High Definition Audio Device)", devices=devices)

        self.assertEqual(device.hostapi_name, "MME")

    def test_find_output_device_accepts_virtual_cable_direction_alias(self) -> None:
        devices = [
            device
            for device in self._list_output_devices(FakeSoundDevice())
            if device.is_virtual_cable
        ]

        device = find_output_device("CABLE Output", devices=devices)

        self.assertIn("CABLE Input", device.name)

    def test_find_output_device_accepts_voicemeeter_recording_alias(self) -> None:
        devices = self._list_output_devices(FakeSoundDevice())

        device = find_output_device("VoiceMeeter Aux Output", devices=devices)

        self.assertIn("VoiceMeeter Aux Input", device.name)

    def test_find_output_device_accepts_voicemeeter_bus_alias(self) -> None:
        devices = self._list_output_devices(FakeSoundDevice())

        device = find_output_device("VoiceMeeter Out B2", devices=devices)

        self.assertIn("VoiceMeeter Aux Input", device.name)

    def test_missing_virtual_cable_raises_clear_error(self) -> None:
        devices = [device for device in self._list_output_devices(FakeSoundDevice()) if not device.is_virtual_cable]

        with self.assertRaises(DeviceResolutionError):
            find_output_device(devices=devices, prefer_virtual_cable=True)

    def test_missing_named_virtual_cable_lists_available_virtual_outputs(self) -> None:
        devices = self._list_output_devices(FakeSoundDevice())

        with self.assertRaises(DeviceResolutionError) as context:
            find_output_device("Missing Cable", devices=devices, prefer_virtual_cable=True)

        self.assertIn("Available virtual outputs:", str(context.exception))
        self.assertIn("CABLE Input", str(context.exception))

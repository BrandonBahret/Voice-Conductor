from __future__ import annotations

import unittest

from voice_synth.audio.router import RouteConfig, normalize_route_name
from voice_synth.types import AudioDevice


def _devices(*, include_virtual: bool = True) -> list[AudioDevice]:
    devices = [
        AudioDevice(
            id=0,
            name="Speakers",
            hostapi="WASAPI",
            max_output_channels=2,
            default_samplerate=48000,
            is_default=True,
        )
    ]
    if include_virtual:
        devices.append(
            AudioDevice(
                id=1,
                name="CABLE Input",
                hostapi="WASAPI",
                max_output_channels=2,
                default_samplerate=48000,
                is_virtual_cable=True,
            )
        )
    return devices


class RouteConfigTests(unittest.TestCase):
    def test_default_routes_include_speakers_and_virtual_mic(self) -> None:
        routes = RouteConfig(
            speaker_device="Speakers",
            mic_device="CABLE Input",
        )

        self.assertEqual(routes.get("speakers").device, "Speakers")
        self.assertEqual(routes.get("mic").device, "CABLE Input")
        self.assertTrue(routes.get("mic").prefer_virtual_cable)

    def test_add_route_normalizes_name(self) -> None:
        routes = RouteConfig()

        routes.add_route(" Stream ", device="CABLE Input", prefer_virtual_cable=True)

        route = routes.get("stream")
        self.assertEqual(route.name, "stream")
        self.assertEqual(route.device, "CABLE Input")
        self.assertTrue(route.prefer_virtual_cable)

    def test_resolve_missing_devices_fills_default_routes_with_device_names(self) -> None:
        routes = RouteConfig()

        result = routes.resolve_missing_devices(devices=_devices())

        self.assertIs(result, routes)
        self.assertEqual(routes.get("speakers").device, "Speakers")
        self.assertEqual(routes.get("mic").device, "CABLE Output")

    def test_resolve_missing_devices_preserves_explicit_devices(self) -> None:
        routes = RouteConfig(speaker_device="Speakers", mic_device="CABLE Input")

        routes.resolve_missing_devices(devices=_devices())

        self.assertEqual(routes.get("speakers").device, "Speakers")
        self.assertEqual(routes.get("mic").device, "CABLE Input")

    def test_resolve_missing_devices_leaves_unresolved_routes_when_discovery_fails(self) -> None:
        routes = RouteConfig()

        routes.resolve_missing_devices(devices=_devices(include_virtual=False))

        self.assertEqual(routes.get("speakers").device, "Speakers")
        self.assertIsNone(routes.get("mic").device)

    def test_unknown_route_raises(self) -> None:
        routes = RouteConfig()

        with self.assertRaisesRegex(ValueError, "Unknown playback route"):
            routes.get("stream")

    def test_empty_route_name_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "route name must not be empty"):
            normalize_route_name(" ")

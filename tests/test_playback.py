from __future__ import annotations

from threading import Event
import unittest
from unittest.mock import patch

import numpy as np

from voice_synth.audio.router import RouteConfig, _RoutePlaybackEngine
from voice_synth.audio.playback import _SoundDeviceAudioWriter
from voice_synth.types import AudioDevice, PlaybackHooks, SynthesizedAudio


class RecordingWriter:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def __call__(self, audio: SynthesizedAudio, device: AudioDevice) -> None:
        self.calls.append((id(audio), device.id))


class OrderedRecordingWriter:
    def __init__(self) -> None:
        self.events: list[str] = []

    def __call__(self, audio: SynthesizedAudio, device: AudioDevice) -> None:
        self.events.append(f"write:{device.id}")


class FailingWriter:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error or RuntimeError("writer boom")
        self.calls = 0

    def __call__(self, audio: SynthesizedAudio, device: AudioDevice) -> None:
        self.calls += 1
        raise self.error


class BlockingWriter:
    def __init__(self) -> None:
        self.calls: list[int] = []
        self.started = Event()
        self.second_started = Event()
        self.release_first = Event()
        self.release_second = Event()

    def __call__(self, audio: SynthesizedAudio, device: AudioDevice) -> None:
        self.calls.append(device.id)
        if len(self.calls) == 1:
            self.started.set()
            self.release_first.wait(timeout=5)
            return
        self.second_started.set()
        self.release_second.wait(timeout=5)


class FakeOutputStream:
    def __init__(self, sd, **kwargs) -> None:
        self.sd = sd
        self.kwargs = kwargs

    def __enter__(self):
        self.sd.streams.append(self.kwargs)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def write(self, samples) -> None:
        self.sd.writes.append(samples)


class FakeSoundDeviceModule:
    def __init__(self) -> None:
        self.streams = []
        self.writes = []

    def OutputStream(self, **kwargs):
        return FakeOutputStream(self, **kwargs)


class RoutePlaybackEngineTests(unittest.TestCase):
    def _build_audio(self) -> SynthesizedAudio:
        return SynthesizedAudio(
            samples=np.zeros((16, 1), dtype=np.float32),
            sample_rate=16000,
            channels=1,
            provider="azure",
        )

    def _build_devices(self) -> list[AudioDevice]:
        return [
            AudioDevice(
                id=0,
                name="Speakers",
                hostapi="WASAPI",
                max_output_channels=2,
                default_samplerate=48000,
                is_default=True,
            ),
            AudioDevice(
                id=1,
                name="CABLE Input (VB-Audio Virtual Cable)",
                hostapi="WASAPI",
                max_output_channels=2,
                default_samplerate=48000,
                is_virtual_cable=True,
            ),
        ]

    def test_multiple_routes_reuse_same_audio_for_two_devices(self) -> None:
        writer = RecordingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)
        audio = self._build_audio()

        result = engine.route(audio, ["speakers", "mic"], devices=self._build_devices())

        self.assertEqual(result.routes, ["speakers", "mic"])
        self.assertEqual(set(result.devices), {"speakers", "mic"})
        self.assertEqual(len(writer.calls), 2)
        self.assertEqual({call[0] for call in writer.calls}, {id(audio)})
        self.assertEqual({call[1] for call in writer.calls}, {0, 1})

    def test_ready_hook_fires_before_playback(self) -> None:
        writer = OrderedRecordingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)

        def on_audio_ready(event) -> None:
            writer.events.append(f"ready:{','.join(event.routes)}")

        engine.route(
            self._build_audio(),
            "speakers",
            devices=self._build_devices(),
            hooks=PlaybackHooks(on_audio_ready=on_audio_ready),
        )

        self.assertEqual(writer.events, ["ready:speakers", "write:0"])

    def test_ready_hook_blocks_playback_until_return(self) -> None:
        writer = OrderedRecordingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)
        ready_returned = Event()

        def on_audio_ready(event) -> None:
            writer.events.append("ready:start")
            self.assertEqual(writer.events, ["ready:start"])
            ready_returned.set()

        engine.route(
            self._build_audio(),
            "speakers",
            devices=self._build_devices(),
            hooks=PlaybackHooks(on_audio_ready=on_audio_ready),
        )

        self.assertTrue(ready_returned.is_set())
        self.assertEqual(writer.events, ["ready:start", "write:0"])

    def test_completion_hook_runs_once_after_success_for_routes(self) -> None:
        writer = RecordingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)
        completions = []

        def on_playback_complete(event) -> None:
            completions.append(event)

        result = engine.route(
            self._build_audio(),
            ["speakers", "mic"],
            devices=self._build_devices(),
            hooks=PlaybackHooks(on_playback_complete=on_playback_complete),
        )

        self.assertEqual(len(completions), 1)
        self.assertIs(completions[0].result, result)
        self.assertIsNone(completions[0].error)
        self.assertEqual(completions[0].routes, ["speakers", "mic"])

    def test_ready_hook_exception_prevents_playback_and_triggers_completion(self) -> None:
        writer = RecordingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)
        completions = []

        def on_audio_ready(event) -> None:
            raise RuntimeError("ready boom")

        def on_playback_complete(event) -> None:
            completions.append(event)

        with self.assertRaisesRegex(RuntimeError, "ready boom"):
            engine.route(
                self._build_audio(),
                "speakers",
                devices=self._build_devices(),
                hooks=PlaybackHooks(
                    on_audio_ready=on_audio_ready,
                    on_playback_complete=on_playback_complete,
                ),
            )

        self.assertEqual(writer.calls, [])
        self.assertEqual(len(completions), 1)
        self.assertIsNone(completions[0].result)
        self.assertIsInstance(completions[0].error, RuntimeError)

    def test_writer_exception_triggers_completion_and_reraises(self) -> None:
        writer = FailingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)
        completions = []

        def on_playback_complete(event) -> None:
            completions.append(event)

        with self.assertRaisesRegex(RuntimeError, "writer boom"):
            engine.route(
                self._build_audio(),
                "speakers",
                devices=self._build_devices(),
                hooks=PlaybackHooks(on_playback_complete=on_playback_complete),
            )

        self.assertEqual(writer.calls, 1)
        self.assertEqual(len(completions), 1)
        self.assertIsNone(completions[0].result)
        self.assertIsInstance(completions[0].error, RuntimeError)

    def test_completion_hook_failure_does_not_replace_original_exception(self) -> None:
        writer = FailingWriter(RuntimeError("playback failure"))
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)

        def on_playback_complete(event) -> None:
            raise RuntimeError("cleanup failure")

        with self.assertRaisesRegex(RuntimeError, "playback failure") as context:
            engine.route(
                self._build_audio(),
                "speakers",
                devices=self._build_devices(),
                hooks=PlaybackHooks(on_playback_complete=on_playback_complete),
            )

        notes = getattr(context.exception, "__notes__", [])
        self.assertTrue(any("cleanup failure" in note for note in notes))

    def test_background_route_returns_before_writer_finishes(self) -> None:
        writer = BlockingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)

        task = engine.route(
            self._build_audio(),
            "speakers",
            background=True,
            devices=self._build_devices(),
        )

        self.assertTrue(writer.started.wait(timeout=1))
        self.assertFalse(task.done())
        writer.release_first.set()
        result = task.result(timeout=2)

        self.assertEqual(result.routes, ["speakers"])
        self.assertEqual(writer.calls, [0])

    def test_background_route_queues_requests_in_order(self) -> None:
        writer = BlockingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)
        audio = self._build_audio()
        devices = self._build_devices()

        first = engine.route(audio, "speakers", background=True, devices=devices)
        second = engine.route(audio, "mic", background=True, devices=devices)

        self.assertTrue(writer.started.wait(timeout=1))
        self.assertFalse(writer.second_started.wait(timeout=0.1))
        writer.release_first.set()
        first.result(timeout=2)
        self.assertTrue(writer.second_started.wait(timeout=1))
        self.assertFalse(second.done())
        writer.release_second.set()
        second_result = second.result(timeout=2)

        self.assertEqual(second_result.routes, ["mic"])
        self.assertEqual(writer.calls, [0, 1])

    def test_background_exception_surfaces_on_task(self) -> None:
        writer = FailingWriter()
        engine = _RoutePlaybackEngine(RouteConfig(), audio_writer=writer)

        task = engine.route(
            self._build_audio(),
            "speakers",
            background=True,
            devices=self._build_devices(),
        )

        with self.assertRaisesRegex(RuntimeError, "writer boom"):
            task.result(timeout=2)
        self.assertIsInstance(task.exception(timeout=0), RuntimeError)


class SoundDeviceAudioWriterTests(unittest.TestCase):
    def test_writes_audio_at_native_sample_rate(self) -> None:
        sd = FakeSoundDeviceModule()
        writer = _SoundDeviceAudioWriter()
        audio = SynthesizedAudio(
            samples=np.zeros((16, 1), dtype=np.float32),
            sample_rate=16000,
            channels=1,
            provider="demo",
        )
        device = AudioDevice(
            id=6,
            name="Speakers",
            hostapi="MME",
            max_output_channels=2,
            default_samplerate=44100,
        )

        with patch("voice_synth.audio.playback._load_sounddevice", return_value=sd):
            writer(audio, device)

        self.assertEqual(sd.streams[0]["samplerate"], 16000)
        self.assertEqual(sd.streams[0]["channels"], 1)
        self.assertEqual(sd.streams[0]["device"], 6)
        self.assertEqual(sd.writes[0].shape, (16, 1))

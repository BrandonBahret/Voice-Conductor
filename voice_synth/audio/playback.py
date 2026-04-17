"""Playback primitives used by the route engine."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

import numpy as np

from voice_synth.audio.devices import _load_sounddevice
from voice_synth.types import (
    AudioDevice,
    PlaybackTask,
    SynthesizedAudio,
)

_T = TypeVar("_T")


class PlaybackQueue:
    """Single-worker queue that serializes background speech playback requests."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="voice-synth-playback",
        )

    def submit(self, fn: Callable[..., _T], *args, **kwargs) -> PlaybackTask[_T]:
        """Schedule work on the playback thread and return a task wrapper."""

        return PlaybackTask(self._executor.submit(fn, *args, **kwargs))


class _SoundDeviceAudioWriter:
    """Adapter that writes normalized audio samples to a resolved sounddevice output."""

    def __init__(self) -> None:
        self._sd = None

    def _load(self):
        if self._sd is not None:
            return self._sd
        sd = _load_sounddevice()
        self._sd = sd
        return sd

    def __call__(self, audio: SynthesizedAudio, device: AudioDevice) -> None:
        """Stream a ``SynthesizedAudio`` buffer to one output device."""

        sd = self._load()
        with sd.OutputStream(
            samplerate=audio.sample_rate,
            channels=audio.channels,
            dtype="float32",
            device=device.id,
        ) as stream:
            stream.write(np.asarray(audio.samples, dtype=np.float32))

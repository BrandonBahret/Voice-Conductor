"""Shared data contracts used across providers, caching, and playback.

Provider implementations should return ``SynthesizedAudio`` so downstream
caches and route engines can work with normalized float32 samples regardless of
the provider's native audio format. Playback events and task wrappers keep the
manager API small without exposing executor internals.
"""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar
import wave

import numpy as np

_T = TypeVar("_T")


@dataclass(slots=True)
class VoiceInfo:
    """Metadata describing a voice exposed by a synthesis provider."""

    id: str
    name: str
    provider: str
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AudioDevice:
    """Description of an output-capable audio device discovered on the host."""

    id: int
    name: str
    hostapi: str | None
    max_output_channels: int
    default_samplerate: float | None
    is_default: bool = False
    is_virtual_cable: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
    hostapi_name: str | None = None

    def __post_init__(self) -> None:
        if self.hostapi_name is None:
            self.hostapi_name = self.hostapi
        elif self.hostapi is None:
            self.hostapi = self.hostapi_name

    @property
    def host_api(self) -> str | None:
        """Compatibility alias for the resolved host API name."""

        return self.hostapi_name


@dataclass(slots=True)
class SynthesizedAudio:
    """Normalized floating-point audio returned by a text-to-speech provider."""

    samples: np.ndarray
    sample_rate: int
    channels: int
    provider: str
    voice: str | None = None
    text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        samples = np.asarray(self.samples, dtype=np.float32)
        if samples.ndim == 1:
            samples = samples.reshape(-1, 1)
        if samples.ndim != 2:
            raise ValueError("samples must be a 1D or 2D array")
        if samples.shape[1] != self.channels:
            raise ValueError("channels must match the sample array shape")
        self.samples = np.clip(samples, -1.0, 1.0)

    @property
    def frame_count(self) -> int:
        """Number of audio frames in the sample buffer."""

        return int(self.samples.shape[0])

    @property
    def duration_seconds(self) -> float:
        """Length of the audio clip in seconds."""

        if self.sample_rate <= 0:
            return 0.0
        return self.frame_count / float(self.sample_rate)

    def to_pcm16_bytes(self) -> bytes:
        """Return the samples encoded as raw signed 16-bit PCM bytes."""

        scaled = np.clip(self.samples, -1.0, 1.0) * np.iinfo(np.int16).max
        return scaled.astype(np.int16).tobytes()

    def to_wav_bytes(self) -> bytes:
        """Return the samples encoded as a WAV file payload."""

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(self.to_pcm16_bytes())
        return buffer.getvalue()

    def copy_to(self, path: str | Path, *, format: str = "wav") -> Path:
        """Write the audio to disk as WAV or raw PCM16 and return the target path."""

        target = Path(path)
        if target.parent != Path("."):
            target.parent.mkdir(parents=True, exist_ok=True)

        normalized_format = format.lower()
        if normalized_format == "wav":
            payload = self.to_wav_bytes()
        elif normalized_format in {"pcm16", "raw"}:
            payload = self.to_pcm16_bytes()
        else:
            raise ValueError("format must be 'wav' or 'pcm16'.")

        target.write_bytes(payload)
        return target

    @classmethod
    def from_wav_bytes(
        cls,
        wav_bytes: bytes,
        *,
        provider: str,
        voice: str | None = None,
        text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "SynthesizedAudio":
        """Build a normalized audio object from WAV file bytes."""

        with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            frames = wav_file.readframes(wav_file.getnframes())

        dtype_map = {
            1: np.int8,
            2: np.int16,
            4: np.int32,
        }
        if sample_width not in dtype_map:
            raise ValueError(f"Unsupported WAV sample width: {sample_width}")

        raw = np.frombuffer(frames, dtype=dtype_map[sample_width]).astype(np.float32)
        scale = float(np.iinfo(dtype_map[sample_width]).max)
        samples = (raw / scale).reshape(-1, channels)
        return cls(
            samples=samples,
            sample_rate=sample_rate,
            channels=channels,
            provider=provider,
            voice=voice,
            text=text,
            metadata=metadata or {},
        )

    @classmethod
    def from_pcm16_bytes(
        cls,
        pcm_bytes: bytes,
        *,
        sample_rate: int,
        channels: int,
        provider: str,
        voice: str | None = None,
        text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "SynthesizedAudio":
        """Build a normalized audio object from raw signed 16-bit PCM bytes."""

        raw = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        samples = (raw / np.iinfo(np.int16).max).reshape(-1, channels)
        return cls(
            samples=samples,
            sample_rate=sample_rate,
            channels=channels,
            provider=provider,
            voice=voice,
            text=text,
            metadata=metadata or {},
        )


@dataclass(slots=True)
class PlaybackResult:
    """Result data returned after audio is played through one or more routes."""

    routes: list[str]
    audio: SynthesizedAudio
    devices: dict[str, AudioDevice]


@dataclass(slots=True)
class PlaybackReadyEvent:
    """Event payload emitted after routes resolve and before playback starts."""

    routes: list[str]
    audio: SynthesizedAudio
    devices: dict[str, AudioDevice]


@dataclass(slots=True)
class PlaybackCompleteEvent:
    """Event payload emitted after playback succeeds or fails."""

    routes: list[str]
    audio: SynthesizedAudio
    devices: dict[str, AudioDevice]
    result: PlaybackResult | None = None
    error: Exception | None = None


@dataclass(slots=True)
class PlaybackHooks:
    """Optional callbacks for playback lifecycle events."""

    on_audio_ready: Callable[[PlaybackReadyEvent], None] | None = None
    on_playback_complete: Callable[[PlaybackCompleteEvent], None] | None = None


@dataclass(frozen=True, slots=True)
class PlaybackTask(Generic[_T]):
    """Thin wrapper around a background playback future."""

    _future: Future[_T]

    def done(self) -> bool:
        """Return whether the background task has finished."""

        return self._future.done()

    def result(self, timeout: float | None = None) -> _T:
        """Return the task result, waiting up to timeout seconds if provided."""

        return self._future.result(timeout=timeout)

    def exception(self, timeout: float | None = None) -> BaseException | None:
        """Return the task exception, waiting up to timeout seconds if provided."""

        return self._future.exception(timeout=timeout)

    def cancel(self) -> bool:
        """Request cancellation of the background task."""

        return self._future.cancel()

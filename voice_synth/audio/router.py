"""Route synthesized audio to configured speaker or virtual-mic outputs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Iterable

from voice_synth.audio.devices import find_output_device, list_output_devices, virtual_mic_device_name
from voice_synth.audio.playback import (
    PlaybackQueue,
    _SoundDeviceAudioWriter,
)
from voice_synth.types import (
    AudioDevice,
    PlaybackCompleteEvent,
    PlaybackHooks,
    PlaybackReadyEvent,
    PlaybackResult,
    PlaybackTask,
    SynthesizedAudio,
)

_AudioWriter = Callable[[SynthesizedAudio, AudioDevice], None]


@dataclass(slots=True)
class AudioRoute:
    """Named playback route with optional device preference information."""

    name: str
    device: str | int | None = None
    prefer_virtual_cable: bool = False


@dataclass(slots=True, init=False)
class RouteConfig:
    """Collection of named audio routes used by ``_RoutePlaybackEngine``."""

    routes: dict[str, AudioRoute] = field(default_factory=dict)

    def __init__(
        self,
        routes: dict[str, AudioRoute] | None = None,
        *,
        speaker_device: str | int | None = None,
        mic_device: str | int | None = None,
    ) -> None:
        """Build speaker and mic routes, or use an explicit route mapping."""

        if routes is None:
            routes = {
                "speakers": AudioRoute("speakers", speaker_device),
                "mic": AudioRoute("mic", mic_device, prefer_virtual_cable=True),
            }
        self.routes = {
            normalize_route_name(name): route
            for name, route in routes.items()
        }
        
    @staticmethod
    def default(speaker: str=None, mic: str=None) -> RouteConfig:
        return RouteConfig(speaker_device=speaker, mic_device=mic)

    def add_route(
        self,
        name: str,
        *,
        device: str | int | None = None,
        prefer_virtual_cable: bool = False,
    ) -> None:
        """Register or replace a named route."""

        normalized = normalize_route_name(name)
        self.routes[normalized] = AudioRoute(
            normalized,
            device,
            prefer_virtual_cable=prefer_virtual_cable,
        )

    def get(self, name: str) -> AudioRoute:
        """Return a route by name, raising with available route names on failure."""

        normalized = normalize_route_name(name)
        try:
            return self.routes[normalized]
        except KeyError as exc:
            available = ", ".join(sorted(self.routes)) or "none"
            raise ValueError(f"Unknown playback route {name!r}. Available routes: {available}.") from exc

    def resolve_missing_devices(
        self,
        *,
        devices: list[AudioDevice] | None = None,
    ) -> "RouteConfig":
        """Fill unset route devices with discovered output device names when possible."""

        try:
            available = devices if devices is not None else list_output_devices()
        except Exception:
            return self

        for route in self.routes.values():
            if route.device is not None:
                continue
            try:
                resolved = find_output_device(
                    devices=available,
                    prefer_virtual_cable=route.prefer_virtual_cable,
                )
                route.device = (
                    virtual_mic_device_name(resolved)
                    if route.prefer_virtual_cable
                    else resolved.name
                )
            except Exception:
                continue
        return self


def normalize_route_name(name: str) -> str:
    """Normalize a user-facing route name to its lookup key."""

    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("route name must not be empty")
    return normalized


class _RoutePlaybackEngine:
    """Resolve route names to devices and play audio through them."""

    def __init__(
        self,
        route_config: RouteConfig | None = None,
        *,
        audio_writer: _AudioWriter | None = None,
        playback_queue: PlaybackQueue | None = None,
        route_config_provider: Callable[[], RouteConfig] | None = None,
    ) -> None:
        """Create a route engine with an optional injectable audio writer."""

        self._route_config = route_config or RouteConfig()
        self._route_config_provider = route_config_provider
        self._audio_writer = audio_writer or _SoundDeviceAudioWriter()
        self._playback_queue = playback_queue or PlaybackQueue()

    @property
    def route_config(self) -> RouteConfig:
        """Return the current route config, resyncing from settings when provided."""

        if self._route_config_provider is not None:
            current = self._route_config_provider()
            if current is not self._route_config:
                self._route_config = current
        return self._route_config

    @route_config.setter
    def route_config(self, route_config: RouteConfig) -> None:
        self._route_config = route_config

    def route(
        self,
        audio: SynthesizedAudio,
        routes: str | Iterable[str] = "speakers",
        *,
        background: bool = False,
        hooks: PlaybackHooks | None = None,
        devices: list[AudioDevice] | None = None,
    ) -> PlaybackResult | PlaybackTask[PlaybackResult]:
        """Route audio immediately or enqueue it for background playback."""

        if background:
            return self._playback_queue.submit(
                self._route_sync,
                audio,
                routes,
                hooks=hooks,
                devices=devices,
            )
        return self._route_sync(audio, routes, hooks=hooks, devices=devices)

    def _route_sync(
        self,
        audio: SynthesizedAudio,
        routes: str | Iterable[str],
        *,
        hooks: PlaybackHooks | None = None,
        devices: list[AudioDevice] | None = None,
    ) -> PlaybackResult:
        """Synchronously resolve devices, notify hooks, and play to all routes."""

        route_names = self._normalize_routes(routes)
        route_devices = self._resolve_routes(route_names, devices=devices)
        ready_event = PlaybackReadyEvent(
            routes=route_names,
            audio=audio,
            devices=route_devices,
        )

        try:
            self._notify_ready(hooks, ready_event)
        except Exception as exc:
            self._notify_complete_for_error(
                hooks,
                routes=route_names,
                audio=audio,
                devices=route_devices,
                error=exc,
            )
            raise

        try:
            self._play_to_devices(audio, list(route_devices.values()))
        except Exception as exc:
            self._notify_complete_for_error(
                hooks,
                routes=route_names,
                audio=audio,
                devices=route_devices,
                error=exc,
            )
            raise

        result = PlaybackResult(
            routes=route_names,
            audio=audio,
            devices=route_devices,
        )
        self._notify_complete(
            hooks,
            PlaybackCompleteEvent(
                routes=route_names,
                audio=audio,
                devices=route_devices,
                result=result,
            ),
        )
        return result

    def _normalize_routes(self, routes: str | Iterable[str]) -> list[str]:
        if isinstance(routes, str):
            candidates = [routes]
        else:
            candidates = list(routes)
        normalized = list(dict.fromkeys(normalize_route_name(route) for route in candidates))
        if not normalized:
            raise ValueError("At least one playback route is required.")
        return normalized

    def _resolve_routes(
        self,
        route_names: list[str],
        *,
        devices: list[AudioDevice] | None,
    ) -> dict[str, AudioDevice]:
        resolved: dict[str, AudioDevice] = {}
        for route_name in route_names:
            route = self.route_config.get(route_name)
            resolved[route_name] = find_output_device(
                route.device,
                devices=devices,
                prefer_virtual_cable=route.prefer_virtual_cable,
            )
        return resolved

    def _play_to_devices(self, audio: SynthesizedAudio, devices: list[AudioDevice]) -> None:
        if len(devices) == 1:
            self._audio_writer(audio, devices[0])
            return
        with ThreadPoolExecutor(max_workers=len(devices)) as executor:
            futures = [executor.submit(self._audio_writer, audio, device) for device in devices]
            for future in futures:
                future.result()

    def _notify_ready(self, hooks: PlaybackHooks | None, event: PlaybackReadyEvent) -> None:
        if hooks is None or hooks.on_audio_ready is None:
            return
        hooks.on_audio_ready(event)

    def _notify_complete(self, hooks: PlaybackHooks | None, event: PlaybackCompleteEvent) -> None:
        if hooks is None or hooks.on_playback_complete is None:
            return
        hooks.on_playback_complete(event)

    def _notify_complete_for_error(
        self,
        hooks: PlaybackHooks | None,
        *,
        routes: list[str],
        audio: SynthesizedAudio,
        devices: dict[str, AudioDevice],
        error: Exception,
    ) -> None:
        try:
            self._notify_complete(
                hooks,
                PlaybackCompleteEvent(
                    routes=routes,
                    audio=audio,
                    devices=devices,
                    error=error,
                ),
            )
        except Exception as complete_exc:
            error.add_note(f"Playback completion hook failed: {complete_exc}")

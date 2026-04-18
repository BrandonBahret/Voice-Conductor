"""Audio device discovery and friendly matching for playback routes.

The manager only writes to output devices, even when a route is named ``mic``:
virtual cables such as VB-CABLE and VoiceMeeter expose playback endpoints that
other apps can receive as microphone input. The alias helpers below bridge those
different naming conventions so users can configure either side's label.
"""

from __future__ import annotations

import re
from typing import Any, NoReturn

from voice_synth.exceptions import DependencyError, DeviceResolutionError
from voice_synth.types import AudioDevice

_VIRTUAL_CABLE_MARKERS = ("cable input", "vb-audio", "virtual cable", "voicemeeter")
_HOSTAPI_PREFERENCE = {
    "mme": 0,
    "windows directsound": 1,
    "windows wasapi": 2,
    "windows wdm-ks": 3,
}

# VoiceMeeter names are directional from different apps' points of view:
# "Input" is the playback endpoint used here, while "Output" and "Out B*"
# are recording-side names that games can expose as microphone choices.
_VOICEMEETER_ALIAS_GROUPS = (
    {
        "voicemeeter input",
        "voicemeeter output",
        "voicemeeter out b1",
        "voicemeeter in 6",
    },
    {
        "voicemeeter aux input",
        "voicemeeter aux output",
        "voicemeeter out b2",
        "voicemeeter in 7",
    },
    {
        "voicemeeter vaio3 input",
        "voicemeeter vaio3 output",
        "voicemeeter out b3",
        "voicemeeter in 8",
    },
)


def _load_sounddevice():
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise DependencyError(
            "Audio playback requires the 'sounddevice' package. Install it with 'pip install voice-synth'."
        ) from exc
    return sd


def _hostapi_name(hostapis: list[dict[str, Any]], index: int | None) -> str | None:
    if index is None or index < 0 or index >= len(hostapis):
        return None
    return hostapis[index].get("name")


def _default_output_index(sd) -> int | None:
    default_devices = getattr(sd.default, "device", None)
    if default_devices is None:
        return None
    return default_devices[1]


def _is_output_device(device_info: dict[str, Any]) -> bool:
    return int(device_info.get("max_output_channels", 0)) > 0


def _build_audio_device(
    index: int,
    device_info: dict[str, Any],
    *,
    hostapis: list[dict[str, Any]],
    default_output: int | None,
) -> AudioDevice:
    name = str(device_info.get("name", f"device-{index}"))
    default_samplerate = device_info.get("default_samplerate")
    return AudioDevice(
        id=index,
        name=name,
        hostapi=(hostapi_name := _hostapi_name(hostapis, device_info.get("hostapi"))),
        hostapi_name=hostapi_name,
        max_output_channels=int(device_info.get("max_output_channels", 0)),
        default_samplerate=float(default_samplerate) if default_samplerate is not None else None,
        is_default=index == default_output,
        is_virtual_cable=is_virtual_cable_name(name),
        raw=dict(device_info),
    )


def is_virtual_cable_name(name: str) -> bool:
    """Return whether a device name looks like a virtual audio cable endpoint."""

    lowered = name.lower()
    return any(marker in lowered for marker in _VIRTUAL_CABLE_MARKERS)


def _normalize_device_name(name: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", name.lower()).split())


def _hostapi_rank(device: AudioDevice) -> int:
    return _HOSTAPI_PREFERENCE.get((device.hostapi or "").lower(), len(_HOSTAPI_PREFERENCE))


def _equivalent_device_sort_key(device: AudioDevice) -> tuple[int, int, int]:
    return (_hostapi_rank(device), -len(device.name), device.id)


def _is_generic_output_name(name: str) -> bool:
    normalized = _normalize_device_name(name)
    return normalized in {"microsoft sound mapper output", "primary sound driver"}


def _same_device_family(left: str, right: str) -> bool:
    normalized_left = _normalize_device_name(left)
    normalized_right = _normalize_device_name(right)
    return (
        normalized_left == normalized_right
        or normalized_left in normalized_right
        or normalized_right in normalized_left
    )


def _prefer_fuller_equivalent_device(device: AudioDevice, devices: list[AudioDevice]) -> AudioDevice:
    if _is_generic_output_name(device.name):
        return device

    candidates = [
        candidate
        for candidate in devices
        if candidate.is_virtual_cable == device.is_virtual_cable
        and not _is_generic_output_name(candidate.name)
        and _same_device_family(device.name, candidate.name)
    ]
    if not candidates:
        return device

    return sorted(candidates, key=_equivalent_device_sort_key)[0]


def _virtual_device_sort_key(device: AudioDevice) -> tuple[int, int, int, int]:
    normalized = _normalize_device_name(device.name)
    if "voicemeeter aux" in normalized:
        family_rank = 0
    elif "voicemeeter" in normalized:
        family_rank = 1
    else:
        family_rank = 2
    return (family_rank, _hostapi_rank(device), -len(device.name), device.id)


def virtual_mic_device_name(device: AudioDevice) -> str:
    """Return the recording-side name for a virtual output when it is recognizable."""

    if not device.is_virtual_cable:
        return device.name

    replacements = (
        ("Aux Input", "Aux Output"),
        ("AUX Input", "AUX Output"),
        ("Input", "Output"),
    )
    for source, target in replacements:
        if source in device.name:
            return device.name.replace(source, target, 1)
    return device.name


def _virtual_cable_aliases(name: str) -> set[str]:
    normalized = _normalize_device_name(name)
    aliases = {normalized}
    if " input " in f" {normalized} ":
        aliases.add(normalized.replace(" input ", " output "))
        aliases.add(normalized.replace(" input ", " "))
    if " output " in f" {normalized} ":
        aliases.add(normalized.replace(" output ", " input "))
        aliases.add(normalized.replace(" output ", " "))
    aliases.update(_voicemeeter_aliases(normalized))
    return {" ".join(alias.split()) for alias in aliases if alias.strip()}


def _voicemeeter_aliases(normalized_name: str) -> set[str]:
    resolved: set[str] = set()
    for group in _VOICEMEETER_ALIAS_GROUPS:
        if any(alias in normalized_name for alias in group):
            resolved.update(group)
    return resolved


def _identifier_aliases(identifier: str, *, virtual_cable: bool) -> set[str]:
    if virtual_cable:
        return _virtual_cable_aliases(identifier)
    return {_normalize_device_name(identifier)}


def list_output_devices() -> list[AudioDevice]:
    """Return output-capable devices reported by ``sounddevice``."""

    sd = _load_sounddevice()
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    default_output = _default_output_index(sd)

    return [
        _build_audio_device(
            index,
            item,
            hostapis=hostapis,
            default_output=default_output,
        )
        for index, item in enumerate(devices)
        if _is_output_device(item)
    ]


def _virtual_output_devices(devices: list[AudioDevice]) -> list[AudioDevice]:
    return [device for device in devices if device.is_virtual_cable]


def _default_output_device(
    devices: list[AudioDevice],
    *,
    prefer_virtual_cable: bool,
) -> AudioDevice:
    if prefer_virtual_cable:
        virtual_devices = _virtual_output_devices(devices)
        if virtual_devices:
            return sorted(virtual_devices, key=_virtual_device_sort_key)[0]
        raise DeviceResolutionError(
            "No virtual cable output device was found. Install and configure VB-CABLE."
        )

    for device in devices:
        if device.is_default:
            return _prefer_fuller_equivalent_device(device, devices)
    return devices[0]


def _find_by_id(identifier: int, devices: list[AudioDevice]) -> AudioDevice | None:
    for device in devices:
        if device.id == identifier:
            return device
    return None


def _find_by_name(identifier: str, devices: list[AudioDevice]) -> AudioDevice | None:
    lowered = identifier.lower()
    exact_matches = [device for device in devices if device.name.lower() == lowered]
    if exact_matches:
        equivalent_matches = [
            device
            for device in devices
            if device.is_virtual_cable == exact_matches[0].is_virtual_cable
            and _same_device_family(identifier, device.name)
        ]
        return sorted(equivalent_matches, key=_equivalent_device_sort_key)[0]

    partial_matches = [device for device in devices if lowered in device.name.lower()]
    if partial_matches:
        return sorted(partial_matches, key=_equivalent_device_sort_key)[0]
    return None


def _aliases_match(query_aliases: set[str], device_aliases: set[str]) -> bool:
    return any(
        query == alias or query in alias or alias in query
        for query in query_aliases
        for alias in device_aliases
    )


def _find_by_alias(identifier: str, devices: list[AudioDevice]) -> AudioDevice | None:
    for device in devices:
        device_aliases = _identifier_aliases(device.name, virtual_cable=device.is_virtual_cable)
        query_aliases = _identifier_aliases(identifier, virtual_cable=device.is_virtual_cable)
        if _aliases_match(query_aliases, device_aliases):
            return device
    return None


def _find_named_device(identifier: str | int, devices: list[AudioDevice]) -> AudioDevice | None:
    if isinstance(identifier, int):
        return _find_by_id(identifier, devices)

    return _find_by_name(identifier, devices) or _find_by_alias(identifier, devices)


def _raise_missing_device(
    identifier: str | int,
    devices: list[AudioDevice],
    *,
    prefer_virtual_cable: bool,
) -> NoReturn:
    virtual_devices = _virtual_output_devices(devices)
    if prefer_virtual_cable and virtual_devices:
        available_virtual = ", ".join(device.name for device in virtual_devices)
        raise DeviceResolutionError(
            f"Could not find output device matching {identifier!r}. "
            f"Available virtual outputs: {available_virtual}. "
            "Clear voice_synth.route_config.routes.mic.device to auto-select the first virtual output."
        )

    raise DeviceResolutionError(f"Could not find output device matching {identifier!r}.")


def find_output_device(
    identifier: str | int | None = None,
    *,
    devices: list[AudioDevice] | None = None,
    prefer_virtual_cable: bool = False,
) -> AudioDevice:
    """Resolve an output device by id, exact/partial name, or virtual-cable alias.

    When ``prefer_virtual_cable`` is true and no identifier is provided, the
    first virtual cable endpoint is selected so game/chat mic routing can work
    without hard-coding a host-specific device index.
    """

    available = devices if devices is not None else list_output_devices()
    if not available:
        raise DeviceResolutionError("No output devices are available.")

    if identifier is None:
        return _default_output_device(available, prefer_virtual_cable=prefer_virtual_cable)

    resolved = _find_named_device(identifier, available)
    if resolved is not None:
        return resolved

    _raise_missing_device(identifier, available, prefer_virtual_cable=prefer_virtual_cable)

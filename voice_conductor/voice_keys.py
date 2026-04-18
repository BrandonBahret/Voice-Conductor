"""Shared voice identity helpers for cache-facing keys."""

from __future__ import annotations

import re

_WINDOWS_PREFIX_PATTERN = re.compile(r"^microsoft\s+", re.IGNORECASE)
_WINDOWS_SUFFIX_PATTERN = re.compile(r"\s+desktop$", re.IGNORECASE)
_NON_KEY_CHARS = re.compile(r"[^a-z0-9_]+")


def normalize_voice_key(provider: str, voice: str | None) -> str:
    """Return a stable provider-qualified voice key for phrase-cache identity."""

    provider_key = provider.strip().lower()
    if not provider_key:
        raise ValueError("provider must not be empty")

    voice_text = (voice or "").strip()
    if not voice_text:
        return f"{provider_key}:"

    if provider_key == "windows":
        voice_text = _WINDOWS_PREFIX_PATTERN.sub("", voice_text)
        voice_text = _WINDOWS_SUFFIX_PATTERN.sub("", voice_text)
        return f"windows:{_slug_key(voice_text)}"
    if provider_key == "kokoro":
        return f"kokoro:{voice_text}"
    if provider_key == "elevenlabs":
        return f"elevenlabs:{voice_text}"
    if voice_text.lower().startswith(f"{provider_key}:"):
        return voice_text.lower()
    return f"{provider_key}:{_slug_key(voice_text)}"


def normalize_voice_config_value(provider: str, voice: str | None) -> str | None:
    """Return the provider-local voice value used in configuration."""

    provider_key = provider.strip().lower()
    if not provider_key:
        raise ValueError("provider must not be empty")

    voice_text = (voice or "").strip()
    if not voice_text:
        return None

    provider_prefix = f"{provider_key}:"
    if voice_text.lower().startswith(provider_prefix):
        voice_text = voice_text[len(provider_prefix) :].strip()

    if provider_key == "windows":
        voice_text = _WINDOWS_PREFIX_PATTERN.sub("", voice_text)
        voice_text = _WINDOWS_SUFFIX_PATTERN.sub("", voice_text)
        return _slug_key(voice_text)

    return voice_text


def _slug_key(value: str) -> str:
    lowered = value.strip().lower().replace("-", "_")
    lowered = _NON_KEY_CHARS.sub("_", lowered)
    return lowered.strip("_")

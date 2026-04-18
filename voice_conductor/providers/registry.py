"""Provider registry used to build available text-to-speech backends.

``ProviderRegistry`` is a process-wide singleton. Factories receive the fully
parsed settings object so provider construction can stay lazy and centrally
configured while custom providers remain discoverable by name throughout the
package.
"""

from __future__ import annotations

from collections.abc import Callable

from voice_conductor.config import Settings
from voice_conductor.exceptions import ProviderError
from voice_conductor.providers.azure import AzureSpeechProvider
from voice_conductor.providers.base import TTSProvider
from voice_conductor.providers.demo import DemoProvider
from voice_conductor.providers.elevenlabs import ElevenLabsProvider
from voice_conductor.providers.kokoro import KokoroProvider
from voice_conductor.providers.windows import WindowsSpeechProvider

ProviderFactory = Callable[[Settings], TTSProvider]


class ProviderRegistry:
    """Mutable singleton mapping of provider names to provider factories."""

    _instance: "ProviderRegistry" | None = None

    def __new__(cls) -> "ProviderRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._factories: dict[str, ProviderFactory] = {}
        self._register_builtins()
        self._initialized = True

    def register(self, name: str, factory: ProviderFactory) -> None:
        """Register or replace a provider factory under a normalized name."""

        normalized = self._normalize_name(name)
        self._factories[normalized] = factory

    def unregister(self, name: str) -> None:
        """Remove a provider factory if it is registered."""

        normalized = self._normalize_name(name)
        self._factories.pop(normalized, None)

    def names(self) -> list[str]:
        """Return registered provider names in insertion order."""

        return list(self._factories)

    def get(self, name: str) -> ProviderFactory:
        """Return the factory for ``name`` or raise ``ProviderError``."""

        normalized = self._normalize_name(name)
        try:
            return self._factories[normalized]
        except KeyError as exc:
            raise ProviderError(f"Unknown provider: {name}") from exc

    def build(self, settings: Settings) -> dict[str, TTSProvider]:
        """Instantiate all registered providers with shared settings."""

        return {name: factory(settings) for name, factory in self._factories.items()}

    def build_provider(self, name: str, settings: Settings) -> TTSProvider:
        """Instantiate the named provider with shared settings."""

        return self.get(name)(settings)

    def _register_builtins(self) -> None:
        self.register("elevenlabs", ElevenLabsProvider)
        self.register("kokoro", KokoroProvider)
        self.register("azure", AzureSpeechProvider)
        self.register("windows", WindowsSpeechProvider)
        self.register("demo", DemoProvider)

    def _normalize_name(self, name: str) -> str:
        normalized = name.strip().lower()
        if not normalized:
            raise ValueError("provider name must not be empty")
        return normalized

def register_provider(name: str, factory: ProviderFactory) -> None:
    """Register a provider in the process-wide singleton registry."""

    ProviderRegistry().register(name, factory)


def unregister_provider(name: str) -> None:
    """Remove a provider from the process-wide singleton registry."""

    ProviderRegistry().unregister(name)


def build_registered_providers(settings: Settings) -> dict[str, TTSProvider]:
    """Build providers from the process-wide singleton registry."""

    return ProviderRegistry().build(settings)

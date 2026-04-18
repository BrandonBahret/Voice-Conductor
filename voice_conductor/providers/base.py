"""Abstract provider contract for text-to-speech backends.

Provider implementations are constructed from the shared ``Settings`` object by
the provider registry. Custom provider authors usually define a small typed
settings class, register that class with ``register_provider_config()``, then
register the provider class or factory with ``register_provider()``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from voice_conductor.config import Settings, load_settings
from voice_conductor.types import SynthesizedAudio, VoiceInfo
from voice_conductor.voice_keys import normalize_voice_key

_ProviderT = TypeVar("_ProviderT", bound="TTSProvider")


def settings_from_provider_or_arg(
    provider_or_settings: Any | None = None,
    settings: Settings | None = None,
) -> Settings:
    """Resolve settings for provider methods that also support class calls.

    Built-in metadata helpers use this to accept either an initialized provider
    instance or an explicit ``Settings`` object. New providers usually only need
    to keep the ``Settings`` object passed to ``__init__`` and read their own
    typed config via ``settings.provider_settings(<provider-name>)``.
    """

    if settings is not None:
        return settings
    if isinstance(provider_or_settings, Settings):
        return provider_or_settings
    provider_settings = getattr(provider_or_settings, "settings", None)
    if isinstance(provider_settings, Settings):
        return provider_settings
    return load_settings()


class TTSProvider(ABC):
    """Interface every synthesis backend must implement.

    Provider settings
    -----------------
    Provider factories receive the fully parsed
    ``voice_conductor.config.Settings`` object. A provider should normally
    accept that object in ``__init__`` and fetch only its provider-local config:

    ::

        @dataclass(slots=True)
        class MyProviderSettings:
            api_key: str | None = None
            default_voice: str = "alloy"

        class MyProvider(TTSProvider):
            name = "my_provider"

            def __init__(self, settings: Settings) -> None:
                self.settings = settings
                self.config = settings.provider_settings(self.name)

    Built-in provider config lives on ``settings.providers.<name>``. Custom
    provider config lives in ``settings.providers.extra`` after its config type
    has been registered. In config files, both use the same public shape:

    ::

        {
          "voice_conductor": {
            "provider_chain": ["my_provider"]
          },
          "providers": {
            "my_provider": {
              "api_key": "...",
              "default_voice": "alloy"
            }
          }
        }

    Registration
    ------------
    Register both pieces before loading a config file or constructing
    ``TTSManager``:

    ::

        from voice_conductor import register_provider, register_provider_config

        register_provider_config("my_provider", MyProviderSettings)
        register_provider("my_provider", MyProvider)

    ``register_provider_config`` tells config loading how to parse and serialize
    ``providers.my_provider``. Dataclasses and simple ``__init__(**payload)``
    classes work without custom hooks; otherwise pass ``from_dict`` and
    ``to_dict`` callbacks.

    ``register_provider`` tells the manager how to build the provider by name.
    The factory may be the provider class itself when it accepts
    ``Settings``, or any callable shaped like ``factory(settings) -> TTSProvider``.
    Users enable the provider by placing the registered name in
    ``voice_conductor.provider_chain`` or by passing it as the provider name to
    manager methods.

    Implementation notes
    --------------------
    ``synthesize`` must return ``SynthesizedAudio`` with normalized float32
    samples. ``list_voices`` should return provider-local ``VoiceInfo`` objects;
    VoiceConductor normalizes voice keys for cache and config use. Include any
    synthesis-affecting options, such as model, speed, or language, in
    ``cache_settings`` so phrase-cache entries do not collide.
    """

    name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether dependencies and credentials are present enough to use."""

        raise NotImplementedError

    def default_voice(self) -> str | None:
        """Return the provider's configured fallback voice, if any."""

        return None

    def cache_settings(self) -> str | dict[str, Any] | None:
        """Return synthesis option state that should split phrase-cache entries."""

        return ""

    def cache_voice_key(self, voice: str | None) -> str:
        """Return the normalized voice identity used by phrase caching."""

        return normalize_voice_key(self.name, voice)

    @abstractmethod
    def synthesize(self, text: str, *, voice: str | None = None) -> SynthesizedAudio:
        """Synthesize ``text`` into normalized ``SynthesizedAudio``."""

        raise NotImplementedError

    @abstractmethod
    def list_voices(self, settings: Settings | None = None) -> list[VoiceInfo]:
        """Return the voices currently exposed by the provider.
        
        @dataclass(slots=True)
        class VoiceInfo:
            id: str
            name: str
            provider: str
            language: str | None = None
            metadata: dict[str, Any] = field(default_factory=dict)
        """

        raise NotImplementedError

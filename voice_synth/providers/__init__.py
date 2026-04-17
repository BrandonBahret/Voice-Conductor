"""Provider classes and registry helpers exported by voice_synth."""

from .azure import AzureSpeechProvider
from .base import TTSProvider
from .demo import DemoProvider
from .elevenlabs import ElevenLabsProvider
from .kokoro import KokoroProvider
from .registry import (
    ProviderRegistry,
    build_registered_providers,
    register_provider,
    unregister_provider,
)
from .windows import WindowsSpeechProvider

__all__ = [
    "AzureSpeechProvider",
    "DemoProvider",
    "ElevenLabsProvider",
    "KokoroProvider",
    "ProviderRegistry",
    "TTSProvider",
    "WindowsSpeechProvider",
    "build_registered_providers",
    "register_provider",
    "unregister_provider",
]

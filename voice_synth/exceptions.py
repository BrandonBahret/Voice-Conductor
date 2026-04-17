"""Exception hierarchy for user-facing voice_synth failures."""


class VoiceSynthError(Exception):
    """Base error for the package."""


class ConfigurationError(VoiceSynthError):
    """Raised when provider configuration is incomplete."""


class DependencyError(VoiceSynthError):
    """Raised when an optional dependency is missing."""


class DeviceResolutionError(VoiceSynthError):
    """Raised when playback devices cannot be resolved."""


class ProviderError(VoiceSynthError):
    """Raised when synthesis fails."""

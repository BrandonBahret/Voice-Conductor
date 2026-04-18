"""Exception hierarchy for user-facing voice_conductor failures."""


class VoiceConductorError(Exception):
    """Base error for the package."""


class ConfigurationError(VoiceConductorError):
    """Raised when provider configuration is incomplete."""


class DependencyError(VoiceConductorError):
    """Raised when an optional dependency is missing."""


class DeviceResolutionError(VoiceConductorError):
    """Raised when playback devices cannot be resolved."""


class ProviderError(VoiceConductorError):
    """Raised when synthesis fails."""

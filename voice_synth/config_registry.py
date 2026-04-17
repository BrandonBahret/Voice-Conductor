"""Registry for typed provider-specific configuration objects."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from typing import Any

ProviderConfigParser = Callable[[dict[str, Any]], Any]
ProviderConfigSerializer = Callable[[Any], dict[str, Any]]


class ProviderConfigRegistry:
    """Mutable singleton mapping provider names to config parse/serialize hooks."""

    _instance: "ProviderConfigRegistry" | None = None

    def __new__(cls) -> "ProviderConfigRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._entries: dict[str, tuple[type[Any], ProviderConfigParser, ProviderConfigSerializer]] = {}
        self._initialized = True

    def register(
        self,
        name: str,
        config_type: type[Any],
        *,
        from_dict: ProviderConfigParser | None = None,
        to_dict: ProviderConfigSerializer | None = None,
    ) -> None:
        """Register or replace a config type under a normalized provider name."""

        normalized = self._normalize_name(name)
        parser = from_dict or self._default_parser(config_type)
        serializer = to_dict or self._default_serializer(config_type)
        self._entries[normalized] = (config_type, parser, serializer)

    def unregister(self, name: str) -> None:
        """Remove a registered config type if present."""

        normalized = self._normalize_name(name)
        self._entries.pop(normalized, None)

    def names(self) -> list[str]:
        """Return registered provider config names in insertion order."""

        return list(self._entries)

    def is_registered(self, name: str) -> bool:
        """Return whether ``name`` has a registered typed config."""

        normalized = self._normalize_name(name)
        return normalized in self._entries

    def config_type(self, name: str) -> type[Any]:
        """Return the registered config type for ``name``."""

        normalized = self._normalize_name(name)
        try:
            return self._entries[normalized][0]
        except KeyError as exc:
            raise KeyError(f"Unknown provider config type: {name}") from exc

    def parse(self, name: str, payload: dict[str, Any]) -> Any:
        """Parse a provider config payload into a registered typed object."""

        normalized = self._normalize_name(name)
        try:
            _, parser, _ = self._entries[normalized]
        except KeyError as exc:
            raise KeyError(f"Unknown provider config type: {name}") from exc
        return parser(dict(payload))

    def serialize(self, name: str, value: Any) -> dict[str, Any]:
        """Serialize a registered provider config object back to a mapping."""

        normalized = self._normalize_name(name)
        try:
            _, _, serializer = self._entries[normalized]
        except KeyError as exc:
            raise KeyError(f"Unknown provider config type: {name}") from exc
        payload = serializer(value)
        if not isinstance(payload, dict):
            raise ValueError(f"Serialized provider config for {normalized} must be a dict.")
        return dict(payload)

    def _default_parser(self, config_type: type[Any]) -> ProviderConfigParser:
        if config_type is dict:
            return lambda payload: dict(payload)

        def parse(payload: dict[str, Any]) -> Any:
            if is_dataclass(config_type):
                return config_type(**payload)
            try:
                return config_type(**payload)
            except TypeError as exc:
                raise TypeError(
                    f"Provider config type {config_type.__name__} requires a custom from_dict parser."
                ) from exc

        return parse

    def _default_serializer(self, config_type: type[Any]) -> ProviderConfigSerializer:
        if config_type is dict:
            return lambda value: dict(value)

        def serialize(value: Any) -> dict[str, Any]:
            if is_dataclass(value):
                payload = asdict(value)
            elif hasattr(value, "__dict__"):
                payload = dict(vars(value))
            else:
                raise TypeError(
                    f"Provider config type {config_type.__name__} requires a custom to_dict serializer."
                )
            if not isinstance(payload, dict):
                raise ValueError(
                    f"Serialized provider config for {config_type.__name__} must be a dict."
                )
            return payload

        return serialize

    def _normalize_name(self, name: str) -> str:
        normalized = str(name).strip().lower()
        if not normalized:
            raise ValueError("provider config name must not be empty")
        return normalized


def register_provider_config(
    name: str,
    config_type: type[Any],
    *,
    from_dict: ProviderConfigParser | None = None,
    to_dict: ProviderConfigSerializer | None = None,
) -> None:
    """Register a provider config type in the process-wide singleton registry."""

    ProviderConfigRegistry().register(
        name,
        config_type,
        from_dict=from_dict,
        to_dict=to_dict,
    )


def unregister_provider_config(name: str) -> None:
    """Remove a provider config type from the process-wide singleton registry."""

    ProviderConfigRegistry().unregister(name)


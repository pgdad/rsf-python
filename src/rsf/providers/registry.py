"""Provider registry: dict-dispatch factory for infrastructure providers."""

from __future__ import annotations

from rsf.providers.base import InfrastructureProvider


class ProviderNotFoundError(KeyError):
    """Raised when a provider name is not registered."""

    pass


_PROVIDERS: dict[str, type[InfrastructureProvider]] = {}


def register_provider(name: str, cls: type[InfrastructureProvider]) -> None:
    """Register a provider class by name.

    Last-write-wins: registering the same name twice overwrites.

    Args:
        name: Provider name (e.g., "terraform", "cdk", "custom").
        cls: Provider class (must be a subclass of InfrastructureProvider).
    """
    _PROVIDERS[name] = cls


def get_provider(name: str) -> InfrastructureProvider:
    """Look up and instantiate a provider by name.

    Args:
        name: Registered provider name.

    Returns:
        An instance of the registered provider class.

    Raises:
        ProviderNotFoundError: If no provider is registered with the given name.
    """
    if name not in _PROVIDERS:
        available = sorted(_PROVIDERS.keys())
        raise ProviderNotFoundError(
            f"Unknown provider: {name}. Available: {available}"
        )
    return _PROVIDERS[name]()


def list_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    return sorted(_PROVIDERS.keys())

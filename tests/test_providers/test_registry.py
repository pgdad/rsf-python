"""Tests for provider registry: register, get, list operations."""

from __future__ import annotations

import pytest

from rsf.providers.base import InfrastructureProvider, PrerequisiteCheck, ProviderContext
from rsf.providers.registry import (
    ProviderNotFoundError,
    _PROVIDERS,
    get_provider,
    list_providers,
    register_provider,
)


class _DummyProvider(InfrastructureProvider):
    """Minimal concrete provider for registry tests."""

    def generate(self, ctx: ProviderContext) -> None:
        pass

    def deploy(self, ctx: ProviderContext) -> None:
        pass

    def teardown(self, ctx: ProviderContext) -> None:
        pass

    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
        return []

    def validate_config(self, ctx: ProviderContext) -> None:
        pass


class _AnotherProvider(InfrastructureProvider):
    """Second concrete provider for registry tests."""

    def generate(self, ctx: ProviderContext) -> None:
        pass

    def deploy(self, ctx: ProviderContext) -> None:
        pass

    def teardown(self, ctx: ProviderContext) -> None:
        pass

    def check_prerequisites(self, ctx: ProviderContext) -> list[PrerequisiteCheck]:
        return []

    def validate_config(self, ctx: ProviderContext) -> None:
        pass


@pytest.fixture(autouse=True)
def _clean_registry():
    """Clear the registry before and after each test."""
    _PROVIDERS.clear()
    yield
    _PROVIDERS.clear()


class TestRegisterProvider:
    """Verify register_provider() behavior."""

    def test_register_stores_provider(self) -> None:
        """register_provider() stores the class by name."""
        register_provider("test", _DummyProvider)
        assert "test" in _PROVIDERS
        assert _PROVIDERS["test"] is _DummyProvider

    def test_register_same_name_overwrites(self) -> None:
        """Registering the same name twice uses last-write-wins."""
        register_provider("test", _DummyProvider)
        register_provider("test", _AnotherProvider)
        assert _PROVIDERS["test"] is _AnotherProvider


class TestGetProvider:
    """Verify get_provider() behavior."""

    def test_returns_instance(self) -> None:
        """get_provider() returns an instance of the registered class."""
        register_provider("test", _DummyProvider)
        provider = get_provider("test")
        assert isinstance(provider, _DummyProvider)
        assert isinstance(provider, InfrastructureProvider)

    def test_unknown_raises_provider_not_found_error(self) -> None:
        """get_provider() raises ProviderNotFoundError for unknown names."""
        with pytest.raises(ProviderNotFoundError, match="Unknown provider: unknown"):
            get_provider("unknown")

    def test_error_shows_available_providers(self) -> None:
        """ProviderNotFoundError message includes available providers."""
        register_provider("alpha", _DummyProvider)
        register_provider("beta", _AnotherProvider)
        with pytest.raises(ProviderNotFoundError, match="alpha"):
            get_provider("unknown")

    def test_provider_not_found_error_is_key_error(self) -> None:
        """ProviderNotFoundError is a subclass of KeyError."""
        assert issubclass(ProviderNotFoundError, KeyError)


class TestListProviders:
    """Verify list_providers() behavior."""

    def test_empty_registry(self) -> None:
        """list_providers() returns empty list when nothing registered."""
        assert list_providers() == []

    def test_returns_sorted_names(self) -> None:
        """list_providers() returns names in sorted order."""
        register_provider("cdk", _DummyProvider)
        register_provider("terraform", _AnotherProvider)
        register_provider("custom", _DummyProvider)
        assert list_providers() == ["cdk", "custom", "terraform"]

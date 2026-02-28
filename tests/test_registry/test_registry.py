"""Tests for the handler registry."""

import tempfile
from pathlib import Path

import pytest

from rsf.registry import (
    clear,
    clear_startup_hooks,
    discover_handlers,
    get_handler,
    get_startup_hooks,
    registered_states,
    startup,
    state,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Clear registry before and after each test."""
    clear()
    clear_startup_hooks()
    yield
    clear()
    clear_startup_hooks()


class TestStateDecorator:
    def test_register_handler(self):
        @state("ProcessOrder")
        def process_order(data):
            return data

        assert "ProcessOrder" in registered_states()
        assert get_handler("ProcessOrder") is process_order

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):

            @state("")
            def handler(data):
                return data

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):

            @state("   ")
            def handler(data):
                return data

    def test_duplicate_raises(self):
        @state("MyState")
        def handler1(data):
            return data

        with pytest.raises(ValueError, match="Duplicate"):

            @state("MyState")
            def handler2(data):
                return data

    def test_multiple_handlers(self):
        @state("State1")
        def h1(data):
            return data

        @state("State2")
        def h2(data):
            return data

        @state("State3")
        def h3(data):
            return data

        assert registered_states() == frozenset({"State1", "State2", "State3"})


class TestGetHandler:
    def test_missing_handler_raises_key_error(self):
        with pytest.raises(KeyError, match="No handler registered"):
            get_handler("NonExistent")

    def test_error_message_lists_registered(self):
        @state("Alpha")
        def h1(data):
            return data

        @state("Beta")
        def h2(data):
            return data

        with pytest.raises(KeyError, match="Alpha.*Beta"):
            get_handler("Gamma")


class TestStartupDecorator:
    def test_register_startup_hook(self):
        @startup
        def init_db():
            pass

        hooks = get_startup_hooks()
        assert len(hooks) == 1
        assert hooks[0] is init_db

    def test_multiple_startup_hooks(self):
        @startup
        def h1():
            pass

        @startup
        def h2():
            pass

        assert len(get_startup_hooks()) == 2

    def test_clear_startup_hooks(self):
        @startup
        def h():
            pass

        assert len(get_startup_hooks()) == 1
        clear_startup_hooks()
        assert len(get_startup_hooks()) == 0


class TestClear:
    def test_clear_handlers(self):
        @state("A")
        def h(data):
            return data

        assert len(registered_states()) == 1
        clear()
        assert len(registered_states()) == 0

    def test_clear_does_not_affect_startup(self):
        @startup
        def h():
            pass

        clear()
        assert len(get_startup_hooks()) == 1


class TestDiscoverHandlers:
    def test_discover_imports_py_files(self, tmp_path):
        handler_file = tmp_path / "my_handler.py"
        handler_file.write_text(
            'from rsf.registry import state\n\n@state("Discovered")\ndef discovered(data):\n    return data\n'
        )

        discover_handlers(tmp_path)
        assert "Discovered" in registered_states()

    def test_discover_skips_underscored_files(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "_private.py").write_text(
            'from rsf.registry import state\n\n@state("Private")\ndef private(data):\n    return data\n'
        )

        discover_handlers(tmp_path)
        assert "Private" not in registered_states()

    def test_discover_nonexistent_dir(self):
        # Should not raise
        discover_handlers(Path("/nonexistent/dir"))

    def test_discover_empty_dir(self, tmp_path):
        # Should not raise
        discover_handlers(tmp_path)
        assert len(registered_states()) == 0

"""Tests for context object model and variable store."""

import pytest

from rsf.context.model import ContextObject, ExecutionContext, StateContext
from rsf.variables.store import VariableStore
from rsf.variables.resolver import is_variable_reference, extract_variable_name
from rsf.io.jsonpath import evaluate_jsonpath


class TestContextObject:
    def test_create_factory(self):
        ctx = ContextObject.create(
            execution_id="exec-123",
            execution_name="MyExec",
            state_name="MyState",
            state_machine_name="MyMachine",
        )
        assert ctx.Execution.Id == "exec-123"
        assert ctx.Execution.Name == "MyExec"
        assert ctx.State.Name == "MyState"
        assert ctx.StateMachine.Name == "MyMachine"
        assert ctx.Execution.StartTime != ""

    def test_default_values(self):
        ctx = ContextObject()
        assert ctx.Execution.Id == ""
        assert ctx.State.RetryCount == 0
        assert ctx.Map.Item.Index == 0

    def test_jsonpath_access(self):
        ctx = ContextObject.create(execution_id="test-id")
        val = evaluate_jsonpath(None, "$$.Execution.Id", context=ctx)
        assert val == "test-id"

    def test_jsonpath_nested(self):
        ctx = ContextObject.create(state_name="ProcessOrder")
        val = evaluate_jsonpath(None, "$$.State.Name", context=ctx)
        assert val == "ProcessOrder"


class TestVariableStore:
    def test_set_and_get(self):
        store = VariableStore()
        store.set("count", 42)
        assert store.get("count") == 42

    def test_get_missing_raises(self):
        store = VariableStore()
        with pytest.raises(KeyError, match="not defined"):
            store.get("missing")

    def test_has(self):
        store = VariableStore()
        store.set("x", 1)
        assert store.has("x")
        assert not store.has("y")

    def test_clear(self):
        store = VariableStore()
        store.set("a", 1)
        store.clear()
        assert not store.has("a")

    def test_all(self):
        store = VariableStore()
        store.set("a", 1)
        store.set("b", 2)
        assert store.all() == {"a": 1, "b": 2}

    def test_jsonpath_variable_reference(self):
        store = VariableStore()
        store.set("myVar", "hello")
        val = evaluate_jsonpath(None, "$myVar", variables=store)
        assert val == "hello"


class TestVariableResolver:
    def test_is_variable_reference(self):
        assert is_variable_reference("$myVar")
        assert is_variable_reference("$count")
        assert is_variable_reference("$_private")

    def test_not_variable_reference(self):
        assert not is_variable_reference("$")
        assert not is_variable_reference("$.path")
        assert not is_variable_reference("$$")
        assert not is_variable_reference("notavar")

    def test_extract_name(self):
        assert extract_variable_name("$myVar") == "myVar"
        assert extract_variable_name("$.path") is None
        assert extract_variable_name("$") is None

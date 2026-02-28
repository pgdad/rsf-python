"""Tests for all intrinsic functions and the recursive descent parser."""

import pytest

from rsf.functions import (
    call_intrinsic,
    evaluate_intrinsic,
    registered_intrinsics,
)
from rsf.functions.parser import IntrinsicParseError


class TestRegistry:
    def test_all_functions_registered(self):
        funcs = registered_intrinsics()
        assert len(funcs) >= 17
        assert "States.Format" in funcs
        assert "States.UUID" in funcs
        assert "States.Array" in funcs

    def test_unknown_function_raises(self):
        with pytest.raises(KeyError, match="Unknown"):
            call_intrinsic("States.NonExistent", [])


class TestStatesFormat:
    def test_basic(self):
        assert call_intrinsic("States.Format", ["Hello {}!", "World"]) == "Hello World!"

    def test_multiple_placeholders(self):
        result = call_intrinsic("States.Format", ["{} + {} = {}", 1, 2, 3])
        assert result == "1 + 2 = 3"

    def test_non_string_args_json_serialized(self):
        result = call_intrinsic("States.Format", ["val={}", {"a": 1}])
        assert result == 'val={"a": 1}'

    def test_wrong_arg_count(self):
        with pytest.raises(ValueError, match="placeholders"):
            call_intrinsic("States.Format", ["{}{}"])


class TestStatesArray:
    def test_empty(self):
        assert call_intrinsic("States.Array", []) == []

    def test_mixed_types(self):
        result = call_intrinsic("States.Array", [1, "two", True, None])
        assert result == [1, "two", True, None]


class TestStatesArrayPartition:
    def test_even_split(self):
        assert call_intrinsic("States.ArrayPartition", [[1, 2, 3, 4], 2]) == [[1, 2], [3, 4]]

    def test_uneven_split(self):
        assert call_intrinsic("States.ArrayPartition", [[1, 2, 3, 4, 5], 2]) == [[1, 2], [3, 4], [5]]


class TestStatesArrayContains:
    def test_contains(self):
        assert call_intrinsic("States.ArrayContains", [[1, 2, 3], 2]) is True

    def test_not_contains(self):
        assert call_intrinsic("States.ArrayContains", [[1, 2, 3], 4]) is False


class TestStatesArrayRange:
    def test_range(self):
        assert call_intrinsic("States.ArrayRange", [1, 9, 2]) == [1, 3, 5, 7, 9]

    def test_single_element(self):
        assert call_intrinsic("States.ArrayRange", [5, 5, 1]) == [5]

    def test_zero_step_raises(self):
        with pytest.raises(ValueError, match="zero"):
            call_intrinsic("States.ArrayRange", [1, 10, 0])


class TestStatesArrayGetItem:
    def test_get(self):
        assert call_intrinsic("States.ArrayGetItem", [["a", "b", "c"], 1]) == "b"

    def test_out_of_range(self):
        with pytest.raises(IndexError):
            call_intrinsic("States.ArrayGetItem", [[], 0])


class TestStatesArrayLength:
    def test_length(self):
        assert call_intrinsic("States.ArrayLength", [[1, 2, 3]]) == 3

    def test_empty(self):
        assert call_intrinsic("States.ArrayLength", [[]]) == 0


class TestStatesArrayUnique:
    def test_unique(self):
        assert call_intrinsic("States.ArrayUnique", [[1, 2, 2, 3, 1]]) == [1, 2, 3]

    def test_already_unique(self):
        assert call_intrinsic("States.ArrayUnique", [[1, 2, 3]]) == [1, 2, 3]


class TestStatesBase64:
    def test_encode_decode_roundtrip(self):
        encoded = call_intrinsic("States.Base64Encode", ["Hello World"])
        decoded = call_intrinsic("States.Base64Decode", [encoded])
        assert decoded == "Hello World"

    def test_encode(self):
        assert call_intrinsic("States.Base64Encode", ["test"]) == "dGVzdA=="


class TestStatesHash:
    def test_sha256(self):
        h = call_intrinsic("States.Hash", ["test", "SHA-256"])
        assert len(h) == 64

    def test_md5(self):
        h = call_intrinsic("States.Hash", ["test", "MD5"])
        assert len(h) == 32

    def test_unsupported_algorithm(self):
        with pytest.raises(ValueError, match="unsupported"):
            call_intrinsic("States.Hash", ["test", "SHA-999"])


class TestStatesMath:
    def test_add_ints(self):
        assert call_intrinsic("States.MathAdd", [5, 3]) == 8

    def test_add_floats(self):
        assert call_intrinsic("States.MathAdd", [1.5, 2.5]) == 4.0

    def test_random_in_range(self):
        for _ in range(20):
            r = call_intrinsic("States.MathRandom", [1, 10])
            assert 1 <= r <= 10


class TestStatesStringSplit:
    def test_split(self):
        assert call_intrinsic("States.StringSplit", ["a,b,c", ","]) == ["a", "b", "c"]


class TestStatesJson:
    def test_string_to_json(self):
        assert call_intrinsic("States.StringToJson", ['{"a": 1}']) == {"a": 1}

    def test_json_to_string(self):
        assert call_intrinsic("States.JsonToString", [{"a": 1}]) == '{"a":1}'


class TestStatesUUID:
    def test_uuid(self):
        u = call_intrinsic("States.UUID", [])
        assert len(u) == 36
        assert u.count("-") == 4


class TestParser:
    def test_simple_function(self):
        result = evaluate_intrinsic("States.MathAdd(10, 20)")
        assert result == 30

    def test_nested_function(self):
        result = evaluate_intrinsic("States.Format('id={}', States.UUID())")
        assert result.startswith("id=")

    def test_string_argument(self):
        result = evaluate_intrinsic("States.Base64Encode('hello')")
        assert result == "aGVsbG8="

    def test_path_reference(self):
        result = evaluate_intrinsic("States.Format('Hello {}', $.name)", data={"name": "Bob"})
        assert result == "Hello Bob"

    def test_boolean_argument(self):
        result = evaluate_intrinsic("States.Array(true, false, null)")
        assert result == [True, False, None]

    def test_max_nesting(self):
        # Build a deeply nested expression
        expr = "1"
        for _ in range(11):
            expr = f"States.MathAdd({expr}, 0)"
        with pytest.raises(IntrinsicParseError, match="nesting"):
            evaluate_intrinsic(expr)

    def test_unterminated_string(self):
        with pytest.raises(IntrinsicParseError, match="Unterminated"):
            evaluate_intrinsic("States.Format('hello)")

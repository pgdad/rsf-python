"""Recursive descent parser for intrinsic function expressions.

Supports:
- Function calls: States.Format('Hello {}', States.UUID())
- Nested calls up to depth 10
- String escaping: States.Format('It\\'s a test')
- Path references as arguments: $.field
- Context references: $$.Execution.Id
- JSON literals: numbers, booleans, null
"""

from __future__ import annotations

from typing import Any

from rsf.functions.registry import call_intrinsic
from rsf.io.jsonpath import evaluate_jsonpath


MAX_NESTING_DEPTH = 10


class IntrinsicParseError(Exception):
    """Raised when an intrinsic function expression cannot be parsed."""


def evaluate_intrinsic(
    expression: str,
    data: Any = None,
    context: Any = None,
    variables: Any = None,
) -> Any:
    """Parse and evaluate an intrinsic function expression.

    Args:
        expression: e.g. "States.Format('Hello {}', $.name)"
        data: Input data for JSONPath resolution.
        context: Context object for $$ references.
        variables: Variable store for $varName references.

    Returns:
        The evaluated result.
    """
    parser = _Parser(expression, data, context, variables)
    result = parser.parse_expression(depth=0)
    parser.skip_whitespace()
    if parser.pos < len(parser.text):
        raise IntrinsicParseError(f"Unexpected characters after expression: '{parser.text[parser.pos :]}'")
    return result


class _Parser:
    """Recursive descent parser for intrinsic expressions."""

    def __init__(
        self,
        text: str,
        data: Any,
        context: Any,
        variables: Any,
    ):
        self.text = text
        self.pos = 0
        self.data = data
        self.context = context
        self.variables = variables

    def parse_expression(self, depth: int) -> Any:
        """Parse a single expression (function call, literal, or path ref)."""
        if depth > MAX_NESTING_DEPTH:
            raise IntrinsicParseError(f"Maximum nesting depth ({MAX_NESTING_DEPTH}) exceeded")

        self.skip_whitespace()

        if self.pos >= len(self.text):
            raise IntrinsicParseError("Unexpected end of expression")

        # Function call: States.xxx(...)
        if self.text[self.pos :].startswith("States."):
            return self.parse_function_call(depth)

        # String literal
        if self.peek() in ("'", '"'):
            return self.parse_string()

        # Null
        if self.text[self.pos :].startswith("null"):
            self.pos += 4
            return None

        # Boolean
        if self.text[self.pos :].startswith("true"):
            self.pos += 4
            return True
        if self.text[self.pos :].startswith("false"):
            self.pos += 5
            return False

        # Path reference: $ or $$
        if self.peek() == "$":
            return self.parse_path_reference()

        # Number
        if self.peek() in "-0123456789":
            return self.parse_number()

        raise IntrinsicParseError(f"Unexpected character at position {self.pos}: '{self.peek()}'")

    def parse_function_call(self, depth: int) -> Any:
        """Parse States.FunctionName(arg1, arg2, ...)."""
        # Read function name
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != "(":
            self.pos += 1
        if self.pos >= len(self.text):
            raise IntrinsicParseError("Expected '(' after function name")

        func_name = self.text[start : self.pos].strip()
        self.pos += 1  # skip '('

        # Parse arguments
        args: list[Any] = []
        self.skip_whitespace()

        if self.pos < len(self.text) and self.text[self.pos] != ")":
            args.append(self.parse_expression(depth + 1))
            self.skip_whitespace()
            while self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1  # skip ','
                self.skip_whitespace()
                args.append(self.parse_expression(depth + 1))
                self.skip_whitespace()

        if self.pos >= len(self.text) or self.text[self.pos] != ")":
            raise IntrinsicParseError(f"Expected ')' to close {func_name}")
        self.pos += 1  # skip ')'

        return call_intrinsic(func_name, args)

    def parse_string(self) -> str:
        """Parse a single-quoted or double-quoted string literal."""
        quote = self.text[self.pos]
        self.pos += 1
        result: list[str] = []
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == "\\":
                self.pos += 1
                if self.pos >= len(self.text):
                    raise IntrinsicParseError("Unterminated escape sequence")
                escaped = self.text[self.pos]
                if escaped == "n":
                    result.append("\n")
                elif escaped == "t":
                    result.append("\t")
                elif escaped == "\\":
                    result.append("\\")
                elif escaped == quote:
                    result.append(quote)
                else:
                    result.append(escaped)
                self.pos += 1
            elif ch == quote:
                self.pos += 1
                return "".join(result)
            else:
                result.append(ch)
                self.pos += 1
        raise IntrinsicParseError("Unterminated string literal")

    def parse_path_reference(self) -> Any:
        """Parse a JSONPath reference ($... or $$...)."""
        start = self.pos
        # Read until we hit a delimiter
        while self.pos < len(self.text) and self.text[self.pos] not in ",) \t\n":
            self.pos += 1
        path = self.text[start : self.pos]
        return evaluate_jsonpath(self.data, path, variables=self.variables, context=self.context)

    def parse_number(self) -> int | float:
        """Parse a numeric literal."""
        start = self.pos
        if self.peek() == "-":
            self.pos += 1
        while self.pos < len(self.text) and self.text[self.pos] in "0123456789":
            self.pos += 1
        if self.pos < len(self.text) and self.text[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos] in "0123456789":
                self.pos += 1
            return float(self.text[start : self.pos])
        return int(self.text[start : self.pos])

    def peek(self) -> str:
        """Return current character without advancing."""
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def skip_whitespace(self) -> None:
        """Skip whitespace characters."""
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r":
            self.pos += 1

"""Tests using YAML fixture files for conformance testing."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rsf.dsl.parser import load_definition
from rsf.dsl.validator import validate_definition

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
VALID_DIR = FIXTURES_DIR / "valid"
INVALID_PYDANTIC_DIR = FIXTURES_DIR / "invalid" / "pydantic"
INVALID_SEMANTIC_DIR = FIXTURES_DIR / "invalid" / "semantic"


class TestValidFixtures:
    @pytest.mark.parametrize(
        "fixture",
        sorted(VALID_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_valid_fixtures_parse(self, fixture):
        """All valid fixtures should parse without Pydantic errors."""
        sm = load_definition(fixture)
        assert sm.start_at is not None
        assert len(sm.states) > 0

    @pytest.mark.parametrize(
        "fixture",
        sorted(VALID_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_valid_fixtures_validate(self, fixture):
        """All valid fixtures should pass semantic validation."""
        sm = load_definition(fixture)
        errors = validate_definition(sm)
        assert len(errors) == 0, f"Unexpected errors: {[e.message for e in errors]}"


class TestInvalidPydanticFixtures:
    @pytest.mark.parametrize(
        "fixture",
        sorted(INVALID_PYDANTIC_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_invalid_pydantic_fixtures_rejected(self, fixture):
        """All Pydantic-invalid fixtures should raise ValidationError."""
        with pytest.raises(ValidationError):
            load_definition(fixture)


class TestInvalidSemanticFixtures:
    @pytest.mark.parametrize(
        "fixture",
        sorted(INVALID_SEMANTIC_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_invalid_semantic_fixtures_have_errors(self, fixture):
        """All semantic-invalid fixtures should produce validation errors."""
        sm = load_definition(fixture)
        errors = validate_definition(sm)
        assert len(errors) > 0, "Expected validation errors but got none"

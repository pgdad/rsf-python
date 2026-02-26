"""Integration tests for the intrinsic-showcase example.

Deploys to real AWS, invokes the durable Lambda, and verifies:
- Lambda return value (SUCCEEDED terminal state)
- CloudWatch log assertions for intrinsic function evaluation
- All 5 I/O pipeline stages exercised

Tests are filled in during Phase 16. This file provides the structure.
"""

import pytest

pytestmark = pytest.mark.integration


class TestIntrinsicShowcaseIntegration:
    """Deploy, invoke, verify, and teardown the intrinsic-showcase example."""

    @pytest.fixture(scope="class")
    def example_name(self):
        return "intrinsic-showcase"

    def test_placeholder(self):
        """Placeholder — Phase 16 implements real assertions."""
        pytest.skip("Phase 16: not yet implemented")

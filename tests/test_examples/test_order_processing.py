"""Integration tests for the order-processing example.

Deploys to real AWS, invokes the durable Lambda, and verifies:
- Lambda return value (SUCCEEDED terminal state)
- CloudWatch log assertions for intermediate state transitions

Tests are filled in during Phase 16. This file provides the structure.
"""

import pytest

pytestmark = pytest.mark.integration


class TestOrderProcessingIntegration:
    """Deploy, invoke, verify, and teardown the order-processing example."""

    @pytest.fixture(scope="class")
    def example_name(self):
        return "order-processing"

    def test_placeholder(self):
        """Placeholder — Phase 16 implements real assertions."""
        pytest.skip("Phase 16: not yet implemented")

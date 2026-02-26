"""Integration tests for the data-pipeline example.

Deploys to real AWS, invokes the durable Lambda, and verifies:
- Lambda return value (SUCCEEDED terminal state)
- CloudWatch log assertions for intermediate state transitions
- DynamoDB read/write operations

Tests are filled in during Phase 16. This file provides the structure.
"""

import pytest

pytestmark = pytest.mark.integration


class TestDataPipelineIntegration:
    """Deploy, invoke, verify, and teardown the data-pipeline example."""

    @pytest.fixture(scope="class")
    def example_name(self):
        return "data-pipeline"

    def test_placeholder(self):
        """Placeholder — Phase 16 implements real assertions."""
        pytest.skip("Phase 16: not yet implemented")

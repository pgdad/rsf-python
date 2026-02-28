import sys
from pathlib import Path

import pytest

# Add example root and project src to path
example_root = Path(__file__).parent.parent
project_root = example_root.parent.parent
sys.path.insert(0, str(example_root))
sys.path.insert(0, str(project_root / "src"))

# Make mock_sdk importable
sys.path.insert(0, str(project_root / "tests"))

from rsf.registry.registry import clear  # noqa: E402


@pytest.fixture(autouse=True)
def clean_registry():
    clear()
    yield
    clear()

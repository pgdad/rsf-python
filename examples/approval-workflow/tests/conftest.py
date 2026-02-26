import sys
from pathlib import Path
import pytest

example_root = Path(__file__).parent.parent
project_root = example_root.parent.parent
sys.path.insert(0, str(example_root))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "tests"))

from rsf.registry.registry import clear

@pytest.fixture(autouse=True)
def clean_registry():
    clear()
    yield
    clear()

import sys
from pathlib import Path

import pytest

_example_root = str(Path(__file__).parent.parent)
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, _example_root)
sys.path.insert(0, str(_project_root / "src"))
sys.path.insert(0, str(_project_root / "tests"))

from rsf.registry.registry import clear  # noqa: E402


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear RSF registry and purge cached handler modules between tests."""
    clear()
    for mod_name in [k for k in sys.modules if k == "handlers" or k.startswith("handlers.")]:
        del sys.modules[mod_name]
    if _example_root in sys.path:
        sys.path.remove(_example_root)
    sys.path.insert(0, _example_root)
    yield
    clear()

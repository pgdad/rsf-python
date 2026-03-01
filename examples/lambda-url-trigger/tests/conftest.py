import sys
from pathlib import Path

import pytest

# Add example root and project src to path
_example_root = str(Path(__file__).parent.parent)
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, _example_root)
sys.path.insert(0, str(_project_root / "src"))

# Make mock_sdk importable
sys.path.insert(0, str(_project_root / "tests"))

from rsf.registry.registry import clear  # noqa: E402


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear RSF registry and purge cached handler modules between tests.

    When running all examples together, each example has its own handlers/
    package. Python caches the first handlers package imported, causing
    ModuleNotFoundError for handlers from other examples. Purging handler
    modules from sys.modules and re-prioritising this example's root on
    sys.path forces re-import from the correct location.
    """
    clear()
    # Purge cached handler modules so this example resolves its own handlers
    for mod_name in [k for k in sys.modules if k == "handlers" or k.startswith("handlers.")]:
        del sys.modules[mod_name]
    # Ensure this example's root is first on sys.path
    if _example_root in sys.path:
        sys.path.remove(_example_root)
    sys.path.insert(0, _example_root)
    yield
    clear()

"""Root conftest for RSF test suite."""


def pytest_addoption(parser):
    """Add custom CLI options."""
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Regenerate snapshot golden files instead of comparing.",
    )

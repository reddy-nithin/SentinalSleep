"""Shared pytest configuration and fixtures for SentinelSleep tests.

Integration tests (marked ``@pytest.mark.integration``) require:
  1. The real ML model to be downloaded (HuggingFace cache).
  2. Real audio fixtures in ``data/test_fixtures/`` — NOT synthetic placeholders.

To run integration tests:
    uv run pytest tests/ --integration

Integration tests are skipped by default to keep ``pytest tests/`` fast
and model-free.
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --integration flag to enable integration test suite."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that require ML models and real audio fixtures.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the 'integration' marker."""
    config.addinivalue_line(
        "markers",
        "integration: requires ML models downloaded and real audio fixtures present.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip integration tests unless --integration flag is passed."""
    if config.getoption("--integration"):
        return  # run everything

    skip_marker = pytest.mark.skip(
        reason="Integration test: requires ML models + real audio fixtures. "
               "Run with: uv run pytest tests/ --integration"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_marker)

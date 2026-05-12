"""Pytest configuration for clarity tests."""

from pathlib import Path

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (requiring AI API access)",
    )


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to clarity fixtures directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def case_dir() -> Path:
    """Path to case studies directory."""
    return Path(__file__).resolve().parents[2] / "case"


@pytest.fixture(scope="session")
def outputs_dir() -> Path:
    """Path to outputs directory."""
    return Path(__file__).resolve().parents[2] / "outputs"
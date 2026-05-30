"""Shared test fixtures and Hypothesis strategies."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_repos_dir():
    """Path to sample repository fixtures."""
    return Path(__file__).parent / "fixtures" / "sample_repos"


@pytest.fixture
def sample_packages_dir():
    """Path to sample Agent Package fixtures."""
    return Path(__file__).parent / "fixtures" / "sample_packages"

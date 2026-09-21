"""Fixtures for the deployment-oriented video indexing tests."""

import importlib.util
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUPPORT_FILE = PROJECT_ROOT / "test_videorag_api" / "tests" / "support.py"


def _load_test_support():
    spec = importlib.util.spec_from_file_location(
        "vimo_video_indexing_test_support", SUPPORT_FILE
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load test support module: {SUPPORT_FILE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUPPORT = _load_test_support()


@pytest.fixture
def api(monkeypatch):
    """Load a fresh copy of the production Flask/API module."""
    monkeypatch.setenv("VIMO_TEST_PRODUCTION_API", "1")
    module = SUPPORT.api_module()
    module.global_imagebind_manager = None
    module.process_manager = None
    return module


@pytest.fixture
def safe_write_json():
    """Provide a cross-platform writer when file replacement is not under test."""
    return SUPPORT.safe_write_json


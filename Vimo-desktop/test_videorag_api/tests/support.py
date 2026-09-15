"""Shared test setup and helpers."""

import json
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock


def prepare_test_environment() -> None:
    certifi_mock = MagicMock()
    certifi_mock.where.return_value = os.devnull
    sys.modules["certifi"] = certifi_mock
    for module_name in (
        "moviepy", "moviepy.editor", "videorag", "videorag._llm",
        "videorag._utils", "videorag._videoutil", "torch", "imagebind",
        "imagebind.models", "imagebind.models.imagebind_model", "setproctitle",
    ):
        sys.modules.setdefault(module_name, MagicMock())


def api_module():
    prepare_test_environment()
    if os.environ.get("VIMO_TEST_PRODUCTION_API") == "1":
        production_api = Path(__file__).resolve().parents[2] / "python_backend" / "videorag_api.py"
        spec = importlib.util.spec_from_file_location("videorag_api", production_api)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load production API module: {production_api}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["videorag_api"] = module
        spec.loader.exec_module(module)
        return module

    api_directory = str(Path(__file__).resolve().parents[1])
    if api_directory not in sys.path:
        sys.path.insert(0, api_directory)
    import videorag_api
    return videorag_api


def safe_write_json(file_path: str, data: dict) -> None:
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def make_process(alive: bool = True) -> MagicMock:
    process = MagicMock()
    process.is_alive.return_value = alive
    process.pid = 12345
    return process

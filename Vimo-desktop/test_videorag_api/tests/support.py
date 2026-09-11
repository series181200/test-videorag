"""Shared test setup and helpers."""

import json
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

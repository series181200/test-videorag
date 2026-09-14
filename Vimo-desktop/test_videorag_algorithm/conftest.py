"""Pytest fixtures that load VideoRAG algorithm modules without package side effects."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import sys
import types

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALGORITHM_ROOT = PROJECT_ROOT / "python_backend" / "videorag"
TEST_PACKAGE = "videorag_algorithm_under_test"


def _optional_module(name: str, **attributes):
    """Use an installed dependency when available; otherwise install a minimal stub."""
    try:
        return importlib.import_module(name)
    except ImportError:
        module = types.ModuleType(name)
        for attribute_name, value in attributes.items():
            setattr(module, attribute_name, value)
        sys.modules[name] = module
        return module


def _prepare_optional_dependencies() -> None:
    numpy = _optional_module("numpy", ndarray=object)
    if not hasattr(numpy, "ndarray"):
        numpy.ndarray = object

    _optional_module("tiktoken")
    _optional_module("openai")

    torch = _optional_module("torch")
    if not hasattr(torch, "device"):
        torch.device = lambda name: name
    if not hasattr(torch, "cuda"):
        torch.cuda = types.SimpleNamespace(is_available=lambda: False)
    if not hasattr(torch, "backends"):
        torch.backends = types.SimpleNamespace(
            mps=types.SimpleNamespace(is_available=lambda: False)
        )


def _load_module(module_name: str, relative_path: str):
    full_name = f"{TEST_PACKAGE}.{module_name}"
    if full_name in sys.modules:
        return sys.modules[full_name]

    path = ALGORITHM_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(full_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load algorithm module: {path}")

    module = importlib.util.module_from_spec(spec)
    # Dataclasses and relative imports expect the module to exist during execution.
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def algorithm_modules():
    """Return isolated source modules used by the unit tests."""
    _prepare_optional_dependencies()

    package = types.ModuleType(TEST_PACKAGE)
    package.__path__ = [str(ALGORITHM_ROOT)]
    sys.modules[TEST_PACKAGE] = package

    splitter = _load_module("_splitter", "_splitter.py")
    utils = _load_module("_utils", "_utils.py")
    base = _load_module("base", "base.py")
    prompt = _load_module("prompt", "prompt.py")

    # _op imports _videoutil only for high-cost retrieved-caption processing. The
    # chunking/entity tests do not need it, so a narrow fake keeps them true unit tests.
    videoutil = types.ModuleType(f"{TEST_PACKAGE}._videoutil")

    async def retrieved_segment_caption_async(*args, **kwargs):
        return {}

    videoutil.retrieved_segment_caption_async = retrieved_segment_caption_async
    sys.modules[videoutil.__name__] = videoutil

    operations = _load_module("_op", "_op.py")

    storage_package = types.ModuleType(f"{TEST_PACKAGE}._storage")
    storage_package.__path__ = [str(ALGORITHM_ROOT / "_storage")]
    sys.modules[storage_package.__name__] = storage_package
    json_storage = _load_module("_storage.kv_json", "_storage/kv_json.py")

    return types.SimpleNamespace(
        splitter=splitter,
        utils=utils,
        base=base,
        prompt=prompt,
        operations=operations,
        json_storage=json_storage,
    )


@pytest.fixture
def fake_tokenizer():
    """Deterministic tokenizer fake used to verify chunk boundaries."""

    class FakeTokenizer:
        @staticmethod
        def encode(text: str):
            return [ord(character) for character in text]

        @classmethod
        def encode_batch(cls, texts, num_threads=None):
            return [cls.encode(text) for text in texts]

        @staticmethod
        def decode(tokens):
            return " ".join(str(token) for token in tokens)

        @classmethod
        def decode_batch(cls, token_batches):
            return [cls.decode(tokens) for tokens in token_batches]

    return FakeTokenizer()

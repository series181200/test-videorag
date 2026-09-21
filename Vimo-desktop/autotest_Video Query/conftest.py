"""Load the production API and replace only external dependencies."""
import importlib.util
import json
import logging
import os
import sys
import types
import warnings
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "python_backend" / "videorag_api.py"


class ControlledProcess:
    """A deferred worker: start records activity, run executes the real target."""
    def __init__(self, target, args):
        self.target, self.args = target, args
        self.pid, self.exitcode = 10000, None
        self.started, self.alive = False, False

    def start(self):
        self.started = self.alive = True

    def is_alive(self):
        return self.alive

    def run(self):
        assert self.started, "Worker cannot run before Process.start"
        try:
            self.target(*self.args)
            self.exitcode = 0
        except BaseException:
            self.exitcode = 1
            raise
        finally:
            self.alive = False

    def terminate(self):
        self.alive, self.exitcode = False, -15

    kill = terminate

    def join(self, timeout=None):
        return None


@pytest.fixture
def api(monkeypatch, tmp_path):
    def module(name, **attrs):
        value = types.ModuleType(name)
        value.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, value)
        return value

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected model/media/network operation in isolated VQ test")

    module("moviepy", __path__=[])
    module("moviepy.editor", VideoFileClip=forbidden)
    module("videorag", __path__=[], VideoRAG=forbidden,
           QueryParam=lambda **kw: types.SimpleNamespace(**kw))
    module("videorag._llm", LLMConfig=lambda **kw: types.SimpleNamespace(**kw),
           openai_embedding=forbidden, gpt_complete=forbidden, dashscope_caption_complete=forbidden)
    module("setproctitle", setproctitle=lambda name: None)
    monkeypatch.setattr(sys, "argv", sys.argv.copy())
    # The production module changes these during import; restore them on teardown.
    monkeypatch.setenv("SSL_CERT_FILE", os.environ.get("SSL_CERT_FILE", ""))
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", os.environ.get("REQUESTS_CA_BUNDLE", ""))
    logger = logging.getLogger("httpx")
    original_level = logger.level
    with warnings.catch_warnings():
        spec = importlib.util.spec_from_file_location("vq_production_api", SOURCE)
        loaded = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, spec.name, loaded)
        spec.loader.exec_module(loaded)
        assert Path(loaded.__file__).resolve() == SOURCE.resolve()
        monkeypatch.setattr(loaded.requests.sessions.Session, "request", forbidden)
        log_path = tmp_path / "api.log"
        def log(message, **kwargs):
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(str(message) + "\n")
        monkeypatch.setattr(loaded, "log_to_file", log)
        try:
            yield loaded
        finally:
            logger.setLevel(original_level)


@pytest.fixture
def runtime(api, monkeypatch, tmp_path):
    processes = []
    def create_process(target, args):
        process = ControlledProcess(target, args)
        process.pid += len(processes)
        processes.append(process)
        return process
    monkeypatch.setattr(api.multiprocessing, "Process", create_process)
    manager = api.VideoRAGProcessManager()
    manager.set_global_config({"base_storage_path": str(tmp_path)})
    monkeypatch.setattr(api, "process_manager", manager)
    app = api.create_app()
    app.config["TESTING"] = True

    class Runtime:
        def prepare(self, state="completed", old_answer=None):
            directory = tmp_path / "chat-vq-session"
            directory.mkdir(exist_ok=True)
            data = {} if state == "none" else {"indexing_status": {"status": state}}
            if state == "completed":
                data["indexed_videos"] = ["lesson"]
            if old_answer is not None:
                data["query_status"] = {"status": "completed", "query": "old question", "answer": old_answer}
            # Fixture preparation writes the input state; all application updates remain real.
            (directory / "status.json").write_text(json.dumps(data), encoding="utf-8")
            return data

        def status(self):
            return json.loads(self.status_file.read_text(encoding="utf-8")) if self.status_file.exists() else {}

        def query(self, text):
            return self.client.post("/api/sessions/vq-session/query", json={"query": text})

    value = Runtime()
    value.api, value.manager, value.client = api, manager, app.test_client()
    value.processes = processes
    value.directory = tmp_path / "chat-vq-session"
    value.status_file = value.directory / "status.json"
    yield value
    for process in processes:
        if process.is_alive():
            process.terminate()


@pytest.fixture
def model(runtime, monkeypatch):
    query = MagicMock(return_value="new answer")
    monkeypatch.setattr(runtime.api, "HTTPImageBindClient", lambda url:
                        types.SimpleNamespace(get_status=lambda: {"initialized": True}))
    monkeypatch.setattr(runtime.api, "VideoRAG", lambda **kwargs: types.SimpleNamespace(query=query))
    return query

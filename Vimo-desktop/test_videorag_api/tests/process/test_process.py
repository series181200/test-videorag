"""Process lifecycle and task scheduling tests implemented with pytest."""

from unittest.mock import MagicMock

from tests.support import api_module, make_process

api = api_module()


def make_manager(base_path):
    manager = api.VideoRAGProcessManager()
    manager.set_global_config({"base_storage_path": str(base_path)})
    return manager


def test_video_indexing_starts_and_is_recorded(tmp_path, monkeypatch):
    process_class = MagicMock()
    process = MagicMock()
    process_class.return_value = process
    monkeypatch.setattr(api.multiprocessing, "Process", process_class)
    manager = make_manager(tmp_path)

    assert manager.start_video_indexing("index-chat", ["video.mp4"]) is True
    process.start.assert_called_once()
    assert "index-chat" in manager.running_processes

    def test_terminate_session_stops_related_processes(self):
        manager = self.manager()
        index_process = make_process()
        query_process = make_process()
        manager.running_processes = {
            "chat-01": {"process": index_process, "type": "video_indexing"},
            "chat-01_query": {"process": query_process, "type": "query_processing"},
        }
        manager.terminate_process("chat-01")
        self.assertFalse(
            manager.running_processes,
            f"终止会话后仍残留进程: {list(manager.running_processes)}",
        )
        index_process.terminate.assert_called_once()
        query_process.terminate.assert_called_once()

def test_terminate_session_stops_related_processes(tmp_path):
    manager = make_manager(tmp_path)
    index_process = make_process()
    query_process = make_process()
    manager.running_processes = {
        "chat-01": {"process": index_process, "type": "video_indexing"},
        "chat-01_query": {"process": query_process, "type": "query_processing"},
    }

    manager.terminate_process("chat-01")

    assert not manager.running_processes
    index_process.terminate.assert_called_once()
    query_process.terminate.assert_called_once()


def test_missing_query_does_not_start_process(monkeypatch):
    app = api.create_app()
    app.config["TESTING"] = True
    process_manager = MagicMock()
    monkeypatch.setattr(api, "process_manager", process_manager)

    response = app.test_client().post("/api/sessions/chat-01/query", json={})

    assert response.status_code == 400
    process_manager.start_query_processing.assert_not_called()

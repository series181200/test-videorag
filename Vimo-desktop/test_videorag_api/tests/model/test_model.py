"""ImageBind and worker error-handling tests implemented with pytest."""

from pathlib import Path
from unittest.mock import MagicMock

from tests.support import api_module, safe_write_json

api = api_module()


def test_index_worker_enters_error_when_imagebind_unavailable(tmp_path, monkeypatch):
    client_class = MagicMock()
    client_class.return_value.get_status.return_value = {"initialized": False}
    monkeypatch.setattr(api, "HTTPImageBindClient", client_class)
    monkeypatch.setattr(api, "write_status_json", safe_write_json)

    api.index_video_worker_process(
        "imagebind-error", [], {"base_storage_path": str(tmp_path)}, "http://localhost"
    )

    path = api.get_session_status_file("imagebind-error", str(tmp_path))
    assert api.read_status_json(path)["indexing_status"]["status"] == "error"


def test_index_worker_enters_error_when_videorag_fails(tmp_path, monkeypatch):
    client_class = MagicMock()
    client_class.return_value.get_status.return_value = {"initialized": True}
    rag_class = MagicMock()
    rag_class.return_value.insert_video.side_effect = RuntimeError("index failed")
    monkeypatch.setattr(api, "HTTPImageBindClient", client_class)
    monkeypatch.setattr(api, "VideoRAG", rag_class)
    monkeypatch.setattr(api, "write_status_json", safe_write_json)

    api.index_video_worker_process(
        "index-error", [], {"base_storage_path": str(tmp_path)}, "http://localhost"
    )

    path = api.get_session_status_file("index-error", str(tmp_path))
    assert api.read_status_json(path)["indexing_status"]["status"] == "error"


def test_query_worker_enters_error_when_query_fails(tmp_path, monkeypatch):
    client_class = MagicMock()
    client_class.return_value.get_status.return_value = {"initialized": True}
    rag_class = MagicMock()
    rag_class.return_value.query.side_effect = RuntimeError("query failed")
    update_status = MagicMock()
    monkeypatch.setattr(api, "HTTPImageBindClient", client_class)
    monkeypatch.setattr(api, "VideoRAG", rag_class)
    monkeypatch.setattr(api, "update_session_status", update_status)
    Path(tmp_path, "chat-query-error").mkdir()

    api.query_worker_process(
        "query-error", "question", {"base_storage_path": str(tmp_path)}, "http://localhost"
    )

    assert any(
        call.args[2] == "query_status" and call.args[3].get("status") == "error"
        for call in update_status.call_args_list
    )

"""ImageBind and worker error handling tests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support import api_module, safe_write_json

api = api_module()


class TestModelFunctions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch.object(api, "HTTPImageBindClient")
    def test_index_worker_enters_error_when_imagebind_unavailable(self, client_class):
        client_class.return_value.get_status.return_value = {"initialized": False}
        with patch.object(api, "write_status_json", side_effect=safe_write_json):
            api.index_video_worker_process(
                "imagebind-error", [], {"base_storage_path": self.base_path}, "http://localhost"
            )
        path = api.get_session_status_file("imagebind-error", self.base_path)
        self.assertEqual(api.read_status_json(path)["indexing_status"]["status"], "error")

    @patch.object(api, "VideoRAG")
    @patch.object(api, "HTTPImageBindClient")
    def test_index_worker_enters_error_when_videorag_fails(self, client_class, rag_class):
        client_class.return_value.get_status.return_value = {"initialized": True}
        rag_class.return_value.insert_video.side_effect = RuntimeError("index failed")
        with patch.object(api, "write_status_json", side_effect=safe_write_json):
            api.index_video_worker_process(
                "index-error", [], {"base_storage_path": self.base_path}, "http://localhost"
            )
        path = api.get_session_status_file("index-error", self.base_path)
        self.assertEqual(api.read_status_json(path)["indexing_status"]["status"], "error")

    @patch.object(api, "VideoRAG")
    @patch.object(api, "HTTPImageBindClient")
    def test_query_worker_enters_error_when_query_fails(self, client_class, rag_class):
        client_class.return_value.get_status.return_value = {"initialized": True}
        rag_class.return_value.query.side_effect = RuntimeError("query failed")
        Path(self.base_path, "chat-query-error").mkdir()
        with patch.object(api, "update_session_status") as update_status:
            api.query_worker_process(
                "query-error", "question", {"base_storage_path": self.base_path}, "http://localhost"
            )
        self.assertTrue(any(
            call.args[2] == "query_status" and call.args[3].get("status") == "error"
            for call in update_status.call_args_list
        ))

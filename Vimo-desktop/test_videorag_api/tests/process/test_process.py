"""Process lifecycle and task scheduling tests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.support import api_module, make_process, safe_write_json

api = api_module()


class TestProcessFunctions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def manager(self):
        manager = api.VideoRAGProcessManager()
        manager.set_global_config({"base_storage_path": self.base_path})
        return manager

    @patch("videorag_api.multiprocessing.Process")
    def test_video_indexing_starts_and_is_recorded(self, process_class):
        process = MagicMock()
        process_class.return_value = process
        manager = self.manager()
        self.assertTrue(manager.start_video_indexing("index-chat", ["video.mp4"]))
        process.start.assert_called_once()
        self.assertIn("index-chat", manager.running_processes)

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

    def test_delete_session_removes_status_directory(self):
        manager = self.manager()
        status_file = api.get_session_status_file("delete-chat", self.base_path)
        api.write_status_json(status_file, {"indexing_status": {"status": "completed"}})

        manager.delete_session("delete-chat")

        self.assertFalse(Path(status_file).parent.exists())

    @patch("videorag_api.multiprocessing.Process")
    def test_duplicate_indexing_is_not_started_twice(self, process_class):
        process_class.return_value = make_process()
        manager = self.manager()
        with patch.object(api, "write_status_json", side_effect=safe_write_json):
            manager.start_video_indexing("duplicate", ["video.mp4"])
            manager.start_video_indexing("duplicate", ["video.mp4"])
        self.assertEqual(process_class.call_count, 1)

    def test_system_status_excludes_finished_processes(self):
        app = api.create_app()
        app.config["TESTING"] = True
        manager = self.manager()
        finished_process = make_process(alive=False)
        manager.running_processes["finished-chat"] = {
            "process": finished_process,
            "type": "video_indexing",
        }
        api.process_manager = manager
        api.global_imagebind_manager = api.GlobalImageBindManager()

        response = app.test_client().get("/api/system/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total_sessions"], 0)

    def test_empty_query_does_not_start_process(self):
        app = api.create_app()
        app.config["TESTING"] = True
        api.process_manager = MagicMock()

        response = app.test_client().post(
            "/api/sessions/chat-01/query", json={"query": ""}
        )

        self.assertEqual(response.status_code, 400)
        api.process_manager.start_query_processing.assert_not_called()

    def test_missing_query_does_not_start_process(self):
        app = api.create_app()
        app.config["TESTING"] = True
        api.process_manager = MagicMock()

        response = app.test_client().post("/api/sessions/chat-01/query", json={})

        self.assertEqual(response.status_code, 400)
        api.process_manager.start_query_processing.assert_not_called()

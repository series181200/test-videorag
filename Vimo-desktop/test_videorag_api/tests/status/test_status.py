"""Status file and concurrent persistence tests."""

import os
import tempfile
import threading
import unittest

from tests.support import api_module

api = api_module()


class TestStatusFunctions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_status_json_write_and_read(self):
        path = os.path.join(self.base_path, "status.json")
        expected = {"indexing_status": {"status": "processing"}}
        api.write_status_json(path, expected)
        self.assertEqual(api.read_status_json(path), expected)

    def test_session_status_merges_index_and_query(self):
        api.update_session_status("status-chat", self.base_path, "indexing_status", {"status": "ok"})
        api.update_session_status("status-chat", self.base_path, "query_status", {"query": "hello"})
        path = api.get_session_status_file("status-chat", self.base_path)
        status = api.read_status_json(path)
        self.assertEqual(status["indexing_status"]["status"], "ok")
        self.assertEqual(status["query_status"]["query"], "hello")

    def test_concurrent_status_updates_are_safe(self):
        errors = []
        barrier = threading.Barrier(2)

        def update(status_type):
            try:
                barrier.wait()
                api.update_session_status(
                    "concurrent", self.base_path, status_type, {"status": "processing"}
                )
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=update, args=("indexing_status",)),
            threading.Thread(target=update, args=("query_status",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertFalse(errors, errors)

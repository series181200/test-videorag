"""HTTP endpoint contract tests."""

import unittest
from unittest.mock import MagicMock

from tests.support import api_module

api = api_module()


class TestApiEndpoints(unittest.TestCase):
    def setUp(self):
        api.global_imagebind_manager = None
        api.process_manager = None
        self.app = api.create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_health_endpoint_is_available(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_initialize_rejects_empty_json_body(self):
        response = self.client.post("/api/initialize", data="", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_imagebind_status_keeps_status_contract(self):
        response = self.client.get("/api/imagebind/status")
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.get_json())

    def test_non_string_query_is_rejected(self):
        response = self.client.post("/api/sessions/chat-01/query", json={"query": 123})
        self.assertEqual(response.status_code, 400)

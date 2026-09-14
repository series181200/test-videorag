"""HTTP endpoint contract tests implemented with pytest."""

import pytest

from tests.support import api_module

api = api_module()


@pytest.fixture
def client():
    """Create an isolated Flask client for every endpoint test."""
    api.global_imagebind_manager = None
    api.process_manager = None
    app = api.create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health_endpoint_is_available(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_initialize_rejects_empty_json_body(client):
    response = client.post("/api/initialize", data="", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_imagebind_status_keeps_status_contract(client):
    response = client.get("/api/imagebind/status")
    assert response.status_code == 200
    assert "status" in response.get_json()


def test_non_string_query_is_rejected(client):
    response = client.post("/api/sessions/chat-01/query", json={"query": 123})
    assert response.status_code == 400

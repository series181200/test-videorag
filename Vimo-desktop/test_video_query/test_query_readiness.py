import pytest
from python_support import require_started


@pytest.mark.parametrize("state,expected", [("missing", 404), ("none", 409), ("processing", 409)],
                         ids=["TC-VQ-002-missing", "TC-VQ-002-unindexed", "TC-VQ-002-indexing"])
def test_query_requires_ready_session(runtime, state, expected):
    if state != "missing":
        runtime.prepare(state)
    before = runtime.status_file.read_bytes() if runtime.status_file.exists() else None
    response = runtime.query("question")
    after = runtime.status_file.read_bytes() if runtime.status_file.exists() else None
    assert {"http": response.status_code, "success": response.get_json().get("success"),
            "created_processes": len(runtime.processes), "state_unchanged": after == before,
            "directory_exists": runtime.directory.exists()} == {
                "http": expected, "success": False, "created_processes": 0,
                "state_unchanged": True, "directory_exists": state != "missing"}


def test_TC_VQ_002_completed_session_can_start_query(runtime):
    runtime.prepare()
    process = require_started(runtime.query("question"), runtime)
    assert process.is_alive()
    assert runtime.manager.running_processes["vq-session_query"]["process"] is process
    assert runtime.status()["query_status"]["query"] == "question"

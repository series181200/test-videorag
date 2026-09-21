"""Assertions shared by the real-manager integration checks."""


def require_started(response, runtime):
    assert response.status_code == 200, (
        "BLOCKED_BEFORE_WORKER: valid query could not start; do not attribute this "
        f"to model recovery or concurrency yet. Response: {response.get_json()}"
    )
    assert response.get_json()["success"] is True
    assert runtime.processes and runtime.processes[-1].started
    return runtime.processes[-1]

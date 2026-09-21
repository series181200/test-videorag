from unittest.mock import MagicMock
import pytest


@pytest.mark.parametrize("query", ["", "   ", "\n", "\t", " \n\t "],
                         ids=["TC-VQ-001-empty", "TC-VQ-001-spaces", "TC-VQ-001-newline", "TC-VQ-001-tab", "TC-VQ-001-mixed"])
def test_blank_query_is_rejected_before_dispatch(runtime, monkeypatch, query):
    before = runtime.prepare()
    # Narrow route-contract check. Real manager integration is exercised separately.
    dispatch = MagicMock(return_value=True)
    monkeypatch.setattr(runtime.manager, "start_query_processing", dispatch)
    response = runtime.query(query)
    observed = {"http": response.status_code, "success": response.get_json().get("success"),
                "dispatches": dispatch.call_count, "processes": len(runtime.processes),
                "state": runtime.status()}
    assert observed == {"http": 400, "success": False, "dispatches": 0, "processes": 0, "state": before}


def test_TC_VQ_001_valid_query_is_trimmed_and_dispatched_once(runtime, monkeypatch):
    runtime.prepare()
    dispatch = MagicMock(return_value=True)
    monkeypatch.setattr(runtime.manager, "start_query_processing", dispatch)
    response = runtime.query("  视频讲了什么？  ")
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    dispatch.assert_called_once_with("vq-session", "视频讲了什么？")

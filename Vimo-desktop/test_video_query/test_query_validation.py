from unittest.mock import MagicMock


def test_TC_VQ_001_whitespace_question_is_not_dispatched(runtime, monkeypatch):
    runtime.prepare()
    dispatch = MagicMock(return_value=True)
    monkeypatch.setattr(runtime.manager, "start_query_processing", dispatch)
    response = runtime.query("   ")
    # Any reasonable client-error status is acceptable; exact wording is irrelevant.
    assert {"client_error": 400 <= response.status_code < 500,
            "success": response.get_json().get("success"),
            "dispatched": dispatch.called} == {
                "client_error": True, "success": False, "dispatched": False}

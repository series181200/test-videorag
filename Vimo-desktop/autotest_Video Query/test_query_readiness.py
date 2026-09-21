def test_TC_VQ_002_nonexistent_session_cannot_start_query(runtime):
    assert not runtime.directory.exists(), "Fixture must start without this session"
    response = runtime.query("视频里讲了什么？")
    assert {"client_error": 400 <= response.status_code < 500,
            "success": response.get_json().get("success"),
            "process_created": bool(runtime.processes),
            "session_created": runtime.directory.exists()} == {
                "client_error": True, "success": False,
                "process_created": False, "session_created": False}

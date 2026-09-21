"""Deployment-oriented automated tests for state management and recovery."""


def make_client(api, monkeypatch, manager):
    """Create a Flask client backed by the supplied process manager."""
    monkeypatch.setattr(api, "process_manager", manager)
    app = api.create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_sr_001_returns_completed_indexing_status(
    api, monkeypatch, tmp_path, safe_write_json
):
    """
    Test Item 测试项：已完成索引任务的状态读取
    Test Type：场景法（基本正常流）
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：会话状态文件记录索引任务已经完成
    Input 输入：GET /api/sessions/chat-completed/status
    Procedure 操作步骤：写入 completed 状态，通过会话状态接口重新读取
    Output 预期结果：返回 HTTP 200、success=true、status=completed 及对应步骤信息
    """
    manager = api.VideoRAGProcessManager()
    manager.set_global_config({"base_storage_path": str(tmp_path)})
    status_file = api.get_session_status_file("chat-completed", str(tmp_path))
    safe_write_json(
        status_file,
        {
            "indexing_status": {
                "status": "completed",
                "message": "All videos processed successfully",
                "current_step": "Completed",
            }
        },
    )
    client = make_client(api, monkeypatch, manager)

    response = client.get("/api/sessions/chat-completed/status")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "chat_id": "chat-completed",
        "status": "completed",
        "message": "All videos processed successfully",
        "current_step": "Completed",
    }


def test_sr_002_returns_not_found_for_unknown_session(api, monkeypatch, tmp_path):
    """
    Test Item 测试项：不存在会话的状态查询
    Test Type：等价类划分（合法异常流）
    Test Criticality 重要级别：High
    Pre-condition 预置条件：全局存储路径已配置，但指定 chat_id 没有状态记录
    Input 输入：GET /api/sessions/chat-unknown/status
    Procedure 操作步骤：查询不存在会话的索引状态并读取HTTP状态和业务状态
    Output 预期结果：返回 HTTP 404、success=false、status=not_found
    """
    manager = api.VideoRAGProcessManager()
    manager.set_global_config({"base_storage_path": str(tmp_path)})
    client = make_client(api, monkeypatch, manager)

    response = client.get("/api/sessions/chat-unknown/status")
    body = response.get_json()

    assert response.status_code == 404
    assert body["success"] is False
    assert body["status"] == "not_found"


def test_sr_003_returns_indexing_and_query_status_independently(
    api, monkeypatch, tmp_path, safe_write_json
):
    """
    Test Item 测试项：同一会话索引状态与查询状态的独立读取
    Test Type：场景法、接口状态选择测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：同一状态文件同时包含已完成索引和正在处理的查询状态
    Input 输入：默认状态请求及带 type=query 的状态请求
    Procedure 操作步骤：分别调用两个状态接口形式，比较返回的状态、问题和答案字段
    Output 预期结果：默认请求返回索引状态，query请求返回查询状态，两者不互相覆盖
    """
    manager = api.VideoRAGProcessManager()
    manager.set_global_config({"base_storage_path": str(tmp_path)})
    status_file = api.get_session_status_file("chat-mixed", str(tmp_path))
    safe_write_json(
        status_file,
        {
            "indexing_status": {
                "status": "completed",
                "message": "Index ready",
                "current_step": "Completed",
            },
            "query_status": {
                "status": "processing",
                "message": "Generating answer",
                "current_step": "Processing",
                "query": "视频讲了什么？",
                "answer": None,
            },
        },
    )
    client = make_client(api, monkeypatch, manager)

    indexing_response = client.get("/api/sessions/chat-mixed/status")
    query_response = client.get("/api/sessions/chat-mixed/status?type=query")
    indexing_body = indexing_response.get_json()
    query_body = query_response.get_json()

    assert indexing_response.status_code == 200
    assert indexing_body["status"] == "completed"
    assert indexing_body["message"] == "Index ready"
    assert query_response.status_code == 200
    assert query_body["status"] == "processing"
    assert query_body["query"] == "视频讲了什么？"
    assert query_body["answer"] is None


def test_sr_004_marks_stale_processing_state_as_interrupted(
    api, monkeypatch, tmp_path, safe_write_json
):
    """
    Test Item 测试项：工作进程异常退出后的残留状态恢复
    Test Type：状态转换测试、异常场景法
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：磁盘状态为 processing，但进程管理器中不存在对应活动进程
    Input 输入：GET /api/sessions/chat-stale/status
    Procedure 操作步骤：写入残留 processing 状态，在无活动进程条件下读取会话状态
    Output 预期结果：返回 interrupted 或 error，不能继续报告 processing
    """
    manager = api.VideoRAGProcessManager()
    manager.set_global_config({"base_storage_path": str(tmp_path)})
    status_file = api.get_session_status_file("chat-stale", str(tmp_path))
    safe_write_json(
        status_file,
        {
            "indexing_status": {
                "status": "processing",
                "message": "Worker was running",
                "current_step": "Embedding",
            }
        },
    )
    client = make_client(api, monkeypatch, manager)

    response = client.get("/api/sessions/chat-stale/status")
    body = response.get_json()

    assert body.get("status") in {"interrupted", "error"}


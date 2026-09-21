"""Deployment-oriented automated tests for the video indexing workflow."""

from unittest.mock import MagicMock


def make_client(api, monkeypatch, manager):
    """Create a Flask client backed by the supplied process manager."""
    monkeypatch.setattr(api, "process_manager", manager)
    app = api.create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_vi_001_accepts_a_normal_video_upload(api, monkeypatch, tmp_path):
    """
    Test Item 测试项：单个有效视频上传与索引任务启动
    Test Type：场景法（基本正常流）
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：VideoRAG API 已初始化，视频路径存在且进程管理器可用
    Input 输入：chat-normal 和 sample.mp4
    Procedure 操作步骤：请求上传接口，检查响应字段以及进程管理器收到的参数
    Output 预期结果：返回 HTTP 200、status=started、数量为 1，并按原路径启动索引
    """
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"controlled video fixture")
    manager = MagicMock()
    manager.start_video_indexing.return_value = True
    client = make_client(api, monkeypatch, manager)

    response = client.post(
        "/api/sessions/chat-normal/videos/upload",
        json={"video_path_list": [str(video_path)]},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body == {
        "success": True,
        "message": "Video processing started",
        "video_names": ["sample"],
        "video_count": 1,
        "chat_id": "chat-normal",
        "status": "started",
    }
    manager.start_video_indexing.assert_called_once_with(
        "chat-normal", [str(video_path)]
    )


def test_vi_002_rejects_a_video_path_that_no_longer_exists(
    api, monkeypatch, tmp_path
):
    """
    Test Item 测试项：视频提交前被移动或删除
    Test Type：场景法（合法异常流）
    Test Criticality 重要级别：High
    Pre-condition 预置条件：用户曾选择视频，但提交索引时源文件已经不存在
    Input 输入：不存在的 moved-video.mp4 路径
    Procedure 操作步骤：请求上传接口并检查响应及进程管理器调用情况
    Output 预期结果：返回 HTTP 400 和失败信息，不创建索引进程
    """
    missing_path = tmp_path / "moved-video.mp4"
    manager = MagicMock()
    manager.start_video_indexing.return_value = True
    client = make_client(api, monkeypatch, manager)

    response = client.post(
        "/api/sessions/chat-missing/videos/upload",
        json={"video_path_list": [str(missing_path)]},
    )
    body = response.get_json()

    assert response.status_code == 400
    assert body["success"] is False
    assert str(missing_path) in body["error"]
    manager.start_video_indexing.assert_not_called()


def test_vi_003_preserves_batch_order_when_starting_indexing(
    api, monkeypatch, tmp_path
):
    """
    Test Item 测试项：多个视频批量上传的顺序与数量
    Test Type：场景法（常用批量流）
    Test Criticality 重要级别：High
    Pre-condition 预置条件：同一会话选择了两个存在的视频文件
    Input 输入：chapter-a.mp4、chapter-b.mkv
    Procedure 操作步骤：按固定顺序提交两个路径，检查响应和索引启动参数
    Output 预期结果：数量为 2、名称及路径顺序不变，并且只启动一次批量索引任务
    """
    first_video = tmp_path / "chapter-a.mp4"
    second_video = tmp_path / "chapter-b.mkv"
    first_video.write_bytes(b"first controlled fixture")
    second_video.write_bytes(b"second controlled fixture")
    paths = [str(first_video), str(second_video)]
    manager = MagicMock()
    manager.start_video_indexing.return_value = True
    client = make_client(api, monkeypatch, manager)

    response = client.post(
        "/api/sessions/chat-batch/videos/upload",
        json={"video_path_list": paths},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["video_names"] == ["chapter-a", "chapter-b"]
    assert body["video_count"] == 2
    manager.start_video_indexing.assert_called_once_with("chat-batch", paths)


def test_vi_004_preserves_unicode_and_space_path_through_indexing_chain(
    api, monkeypatch, tmp_path, safe_write_json
):
    """
    Test Item 测试项：Windows 中文及空格路径的完整传递
    Test Type：场景法、兼容性测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：视频位于包含中文和空格的真实路径，外部模型依赖使用受控替身
    Input 输入：测试视频/课程 01/演示视频.mp4
    Procedure 操作步骤：经上传接口传给进程管理器，再执行索引 worker 并检查算法收到的路径
    Output 预期结果：API、进程管理器和 VideoRAG.insert_video 收到完全相同的原始路径
    """
    video_dir = tmp_path / "测试视频" / "课程 01"
    video_dir.mkdir(parents=True)
    video_path = video_dir / "演示视频.mp4"
    video_path.write_bytes(b"controlled video fixture")

    manager = MagicMock()
    manager.start_video_indexing.return_value = True
    client = make_client(api, monkeypatch, manager)
    response = client.post(
        "/api/sessions/chat-unicode/videos/upload",
        json={"video_path_list": [str(video_path)]},
    )

    assert response.status_code == 200
    manager.start_video_indexing.assert_called_once_with(
        "chat-unicode", [str(video_path)]
    )

    imagebind_client = MagicMock()
    imagebind_client.return_value.get_status.return_value = {"initialized": True}
    rag_class = MagicMock()
    monkeypatch.setattr(api, "HTTPImageBindClient", imagebind_client)
    monkeypatch.setattr(api, "VideoRAG", rag_class)
    monkeypatch.setattr(api, "write_status_json", safe_write_json)

    api.index_video_worker_process(
        "chat-unicode",
        [str(video_path)],
        {"base_storage_path": str(tmp_path)},
        "http://localhost:64451",
    )

    call_kwargs = rag_class.return_value.insert_video.call_args.kwargs
    assert call_kwargs["video_path_list"] == [str(video_path)]


def test_vi_005_keeps_multi_dot_video_names_distinct(api, monkeypatch, tmp_path):
    """
    Test Item 测试项：多点号视频文件名的索引标识
    Test Type：等价类划分、冲突测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：同一会话中存在两个前缀相同但点号后缀不同的视频
    Input 输入：lesson.01.mp4、lesson.02.mp4
    Procedure 操作步骤：同时提交两个文件并读取上传接口返回的视频名称列表
    Output 预期结果：返回 lesson.01 和 lesson.02 两个不同标识，不发生覆盖或误判重复
    """
    first_video = tmp_path / "lesson.01.mp4"
    second_video = tmp_path / "lesson.02.mp4"
    first_video.write_bytes(b"first")
    second_video.write_bytes(b"second")
    manager = MagicMock()
    manager.start_video_indexing.return_value = True
    client = make_client(api, monkeypatch, manager)

    response = client.post(
        "/api/sessions/chat-multidot/videos/upload",
        json={"video_path_list": [str(first_video), str(second_video)]},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["video_names"] == ["lesson.01", "lesson.02"]
    assert len(set(body["video_names"])) == 2


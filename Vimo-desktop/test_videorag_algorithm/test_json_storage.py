"""Unit tests for python_backend/videorag/_storage/kv_json.py."""

import asyncio
import json


def make_storage(algorithm_modules, tmp_path, namespace="unit"):
    return algorithm_modules.json_storage.JsonKVStorage(
        namespace=namespace,
        global_config={"working_dir": str(tmp_path)},
    )


def test_new_storage_starts_empty(algorithm_modules, tmp_path):
    """
    Test Item 测试项：`JsonKVStorage.__post_init__` 无文件分支
    Test Type：等价类划分（文件不存在）
    Test Criticality 重要级别：High
    Pre-condition 预置条件：`tmp_path` 中没有 KV 文件
    Input 输入：namespace=`unit`
    Procedure 操作步骤：创建 storage，再异步读取全部 key
    Output 预期结果：初始化成功，`all_keys()` 返回空列表
    """
    storage = make_storage(algorithm_modules, tmp_path)

    assert asyncio.run(storage.all_keys()) == []


def test_upsert_and_get_by_id(algorithm_modules, tmp_path):
    """
    Test Item 测试项：`JsonKVStorage.upsert/get_by_id`
    Test Type：CRUD 功能测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：新建空 storage
    Input 输入：`id-1 -> {'content':'A'}`
    Procedure 操作步骤：upsert 后按 ID 查询，并查询不存在 ID
    Output 预期结果：已有 ID 返回完整字典；不存在 ID 返回 `None`
    """
    storage = make_storage(algorithm_modules, tmp_path)

    asyncio.run(storage.upsert({"id-1": {"content": "A"}}))

    assert asyncio.run(storage.get_by_id("id-1")) == {"content": "A"}
    assert asyncio.run(storage.get_by_id("missing")) is None


def test_get_by_ids_preserves_order_and_projects_fields(algorithm_modules, tmp_path):
    """
    Test Item 测试项：`JsonKVStorage.get_by_ids` 字段投影
    Test Type：等价类划分、顺序测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：storage 含两个多字段对象
    Input 输入：ID 顺序 `[id-2,missing,id-1]`，fields=`{'content'}`
    Procedure 操作步骤：批量查询并比较结果位置和字段集合
    Output 预期结果：顺序与输入 ID 一致；缺失项为 `None`；只返回 content 字段
    """
    storage = make_storage(algorithm_modules, tmp_path)
    asyncio.run(
        storage.upsert(
            {
                "id-1": {"content": "A", "secret": 1},
                "id-2": {"content": "B", "secret": 2},
            }
        )
    )

    result = asyncio.run(
        storage.get_by_ids(["id-2", "missing", "id-1"], fields={"content"})
    )

    assert result == [{"content": "B"}, None, {"content": "A"}]


def test_filter_keys_returns_only_missing_ids(algorithm_modules, tmp_path):
    """
    Test Item 测试项：`JsonKVStorage.filter_keys`
    Test Type：等价类划分
    Test Criticality 重要级别：High
    Pre-condition 预置条件：`id-1` 已存在
    Input 输入：`[id-1,id-2,id-2]`
    Procedure 操作步骤：调用过滤函数并比较集合
    Output 预期结果：仅返回缺失的 `id-2`，重复输入被集合去重
    """
    storage = make_storage(algorithm_modules, tmp_path)
    asyncio.run(storage.upsert({"id-1": {"content": "A"}}))

    result = asyncio.run(storage.filter_keys(["id-1", "id-2", "id-2"]))

    assert result == {"id-2"}


def test_index_done_callback_persists_and_reloads_json(algorithm_modules, tmp_path):
    """
    Test Item 测试项：`JsonKVStorage.index_done_callback`
    Test Type：持久化契约测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：可写临时目录
    Input 输入：两个 KV 对象
    Procedure 操作步骤：upsert、执行 done callback、读取磁盘 JSON，再创建同 namespace 新实例
    Output 预期结果：文件内容正确，新实例能加载完全相同的数据
    """
    storage = make_storage(algorithm_modules, tmp_path)
    data = {"id-1": {"content": "A"}, "id-2": {"content": "B"}}
    asyncio.run(storage.upsert(data))

    asyncio.run(storage.index_done_callback())

    file_path = tmp_path / "kv_store_unit.json"
    assert json.loads(file_path.read_text(encoding="utf-8")) == data
    reloaded = make_storage(algorithm_modules, tmp_path)
    assert asyncio.run(reloaded.get_by_ids(["id-1", "id-2"])) == [
        data["id-1"],
        data["id-2"],
    ]


def test_drop_clears_memory_and_can_persist_empty_state(algorithm_modules, tmp_path):
    """
    Test Item 测试项：`JsonKVStorage.drop`
    Test Type：状态迁移测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：storage 已包含并持久化一个对象
    Input 输入：调用 `drop` 后再调用 done callback
    Procedure 操作步骤：检查内存 key 和磁盘 JSON
    Output 预期结果：内存 key 为空，持久化文件内容为 `{}`
    """
    storage = make_storage(algorithm_modules, tmp_path)
    asyncio.run(storage.upsert({"id-1": {"content": "A"}}))
    asyncio.run(storage.index_done_callback())

    asyncio.run(storage.drop())
    asyncio.run(storage.index_done_callback())

    assert asyncio.run(storage.all_keys()) == []
    assert json.loads((tmp_path / "kv_store_unit.json").read_text("utf-8")) == {}

"""Selected daily-use regression tests for the VideoRAG algorithm layer."""

import asyncio
import json

import pytest


def make_storage(algorithm_modules, tmp_path, namespace="unit"):
    return algorithm_modules.json_storage.JsonKVStorage(
        namespace=namespace,
        global_config={"working_dir": str(tmp_path)},
    )


def test_query_param_defaults_match_default_query_strategy(algorithm_modules):
    """
    Test Item 测试项：`QueryParam` 默认配置
    Test Type：默认值测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：无
    Input 输入：无参数构造
    Procedure 操作步骤：创建对象并读取查询模式、top_k、层级和 context 开关
    Output 预期结果：mode=`global`、top_k=20、level=2、only_need_context=False
    """
    params = algorithm_modules.base.QueryParam()

    assert params.mode == "global"
    assert params.top_k == 20
    assert params.level == 2
    assert params.only_need_context is False


def test_locate_json_inside_model_response(algorithm_modules):
    """
    Test Item 测试项：`locate_json_string_body_from_string`
    Test Type：等价类划分（含包装文本的合法 JSON）
    Test Criticality 重要级别：High
    Pre-condition 预置条件：无
    Input 输入：`answer: {"name":"demo"} done`
    Procedure 操作步骤：调用提取函数并解析返回字符串
    Output 预期结果：精确提取 JSON 对象文本，且可被 `json.loads` 解析
    """
    result = algorithm_modules.utils.locate_json_string_body_from_string(
        'answer: {"name":"demo"} done'
    )

    assert json.loads(result) == {"name": "demo"}


def test_truncate_list_uses_inclusive_token_boundary(algorithm_modules, monkeypatch):
    """
    Test Item 测试项：`truncate_list_by_token_size`
    Test Type：边界值分析
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：tokenizer fake 令字符数等于 token 数
    Input 输入：`['aa','bbb','c']`，上限 5
    Procedure 操作步骤：累加 token，测试恰好等于上限与超过上限两个边界
    Output 预期结果：保留前两项，总 token 恰为 5；第三项被截断
    """
    monkeypatch.setattr(
        algorithm_modules.utils,
        "encode_string_by_tiktoken",
        lambda content, model_name="gpt-4o": list(content),
    )

    result = algorithm_modules.utils.truncate_list_by_token_size(
        ["aa", "bbb", "c"], key=lambda item: item, max_token_size=5
    )

    assert result == ["aa", "bbb"]


def test_token_size_chunking_obeys_size_and_overlap(algorithm_modules, fake_tokenizer):
    """
    Test Item 测试项：`chunking_by_token_size` 正常窗口分块
    Test Type：边界值分析
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：fake tokenizer 可确定性解码
    Input 输入：6 个 token，`max=4`、`overlap=1`
    Procedure 操作步骤：调用函数并检查块长度、内容、序号和文档 ID
    Output 预期结果：生成两块；第二块从第一块最后一个 token 开始；元数据正确
    """
    result = algorithm_modules.operations.chunking_by_token_size(
        [[1, 2, 3, 4, 5, 6]],
        doc_keys=["doc-1"],
        tiktoken_model=fake_tokenizer,
        overlap_token_size=1,
        max_token_size=4,
    )

    assert result == [
        {
            "tokens": 4,
            "content": "1 2 3 4",
            "chunk_order_index": 0,
            "full_doc_id": "doc-1",
        },
        {
            "tokens": 3,
            "content": "4 5 6",
            "chunk_order_index": 1,
            "full_doc_id": "doc-1",
        },
    ]


def test_video_segments_are_grouped_without_crossing_limit(
    algorithm_modules, fake_tokenizer
):
    """
    Test Item 测试项：`chunking_by_video_segments` 分段合并
    Test Type：边界值分析
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：最大块大小为 3
    Input 输入：`[[1,2],[3],[4,5]]` 及三个 segment ID
    Procedure 操作步骤：顺序累加 segment，检查结果块和关联 ID
    Output 预期结果：前两个 segment 恰好合成 3 token 块，第三个单独成块；无块超限
    """
    result = algorithm_modules.operations.chunking_by_video_segments(
        [[1, 2], [3], [4, 5]],
        doc_keys=["video_0", "video_1", "video_2"],
        tiktoken_model=fake_tokenizer,
        max_token_size=3,
    )

    assert result == [
        {
            "tokens": 3,
            "content": "1 2 3",
            "chunk_order_index": 0,
            "video_segment_id": ["video_0", "video_1"],
        },
        {
            "tokens": 2,
            "content": "4 5",
            "chunk_order_index": 1,
            "video_segment_id": ["video_2"],
        },
    ]


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


def test_async_limit_releases_capacity_after_exception(algorithm_modules):
    """
    Test Item 测试项：`limit_async_func_call` 异常后的容量释放
    Test Type：故障注入、并发测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：并发容量为 1
    Input 输入：第一次调用抛 `RuntimeError`，第二次正常
    Procedure 操作步骤：捕获第一次异常，再对第二次调用设置 0.05 秒超时
    Output 预期结果：第二次调用在超时前返回 `recovered`，说明容量已释放
    """

    async def scenario():
        @algorithm_modules.utils.limit_async_func_call(1, waitting_time=0.001)
        async def operation(should_fail):
            if should_fail:
                raise RuntimeError("boom")
            return "recovered"

        with pytest.raises(RuntimeError, match="boom"):
            await operation(True)
        return await asyncio.wait_for(operation(False), timeout=0.05)

    try:
        actual = asyncio.run(scenario())
    except TimeoutError:
        actual = "timeout: capacity was not released"

    assert actual == "recovered"


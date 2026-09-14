"""Unit tests for python_backend/videorag/_utils.py."""

import asyncio
import json

import pytest


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


def test_locate_json_returns_none_when_object_is_absent(algorithm_modules):
    """
    Test Item 测试项：`locate_json_string_body_from_string`
    Test Type：无效等价类
    Test Criticality 重要级别：Medium
    Pre-condition 预置条件：无
    Input 输入：普通自然语言，无花括号
    Procedure 操作步骤：调用 JSON 定位函数
    Output 预期结果：返回 `None`，不伪造数据
    """
    assert (
        algorithm_modules.utils.locate_json_string_body_from_string("plain answer")
        is None
    )


def test_convert_response_to_json_rejects_missing_json(algorithm_modules):
    """
    Test Item 测试项：`convert_response_to_json` 错误处理
    Test Type：异常测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：无
    Input 输入：`no structured output`
    Procedure 操作步骤：调用转换函数并捕获异常
    Output 预期结果：抛出 `AssertionError`，错误消息说明无法解析 JSON
    """
    with pytest.raises(AssertionError, match="Unable to parse JSON"):
        algorithm_modules.utils.convert_response_to_json("no structured output")


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


def test_truncate_list_rejects_non_positive_budget(algorithm_modules):
    """
    Test Item 测试项：`truncate_list_by_token_size` 非正预算
    Test Type：边界值分析
    Test Criticality 重要级别：High
    Pre-condition 预置条件：key 不应被调用
    Input 输入：列表 `[1,2]`，预算 `0` 和 `-1`
    Procedure 操作步骤：分别调用函数并检查返回值
    Output 预期结果：两种情况均立即返回空列表
    """
    exploding_key = lambda item: (_ for _ in ()).throw(AssertionError("called"))

    assert algorithm_modules.utils.truncate_list_by_token_size(
        [1, 2], exploding_key, 0
    ) == []
    assert algorithm_modules.utils.truncate_list_by_token_size(
        [1, 2], exploding_key, -1
    ) == []


def test_hash_is_deterministic_and_preserves_prefix(algorithm_modules):
    """
    Test Item 测试项：`compute_mdhash_id`
    Test Type：重复性测试、等价类划分
    Test Criticality 重要级别：High
    Pre-condition 预置条件：无
    Input 输入：内容 `video chunk`、前缀 `chunk-`
    Procedure 操作步骤：对相同输入调用两次，并对不同输入调用一次
    Output 预期结果：相同输入 ID 相同、不同输入 ID 不同、结果以前缀开始
    """
    first = algorithm_modules.utils.compute_mdhash_id("video chunk", "chunk-")
    second = algorithm_modules.utils.compute_mdhash_id("video chunk", "chunk-")
    different = algorithm_modules.utils.compute_mdhash_id("other chunk", "chunk-")

    assert first == second
    assert first != different
    assert first.startswith("chunk-")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12", True),
        ("-0.5", True),
        ("+.25", True),
        ("1.", False),
        ("NaN", False),
        ("1e3", False),
        ("", False),
    ],
)
def test_float_recognition_equivalence_classes(algorithm_modules, value, expected):
    """
    Test Item 测试项：`is_float_regex`
    Test Type：等价类划分、参数化测试
    Test Criticality 重要级别：Medium
    Pre-condition 预置条件：无
    Input 输入：整数、正负小数、尾随点、NaN、科学计数法、空串
    Procedure 操作步骤：参数化调用并比较布尔值
    Output 预期结果：普通整数/小数为真；不支持的格式和空串为假
    """
    assert algorithm_modules.utils.is_float_regex(value) is expected


def test_split_string_supports_multiple_markers(algorithm_modules):
    """
    Test Item 测试项：`split_string_by_multi_markers`
    Test Type：组合测试
    Test Criticality 重要级别：Medium
    Pre-condition 预置条件：两种 marker 同时配置
    Input 输入：`A<SEP>B|C`，markers 为 `<SEP>`、`|`
    Procedure 操作步骤：按多个 marker 切分并清理空白
    Output 预期结果：返回 `['A','B','C']`，marker 不进入结果
    """
    result = algorithm_modules.utils.split_string_by_multi_markers(
        " A<SEP>B | C ", ["<SEP>", "|"]
    )

    assert result == ["A", "B", "C"]


def test_clean_str_decodes_html_and_removes_control_characters(algorithm_modules):
    """
    Test Item 测试项：`clean_str`
    Test Type：等价类划分、错误推测
    Test Criticality 重要级别：High
    Pre-condition 预置条件：无
    Input 输入：含首尾空白、`&amp;`、换行和 `\x00`
    Procedure 操作步骤：调用清理函数
    Output 预期结果：去首尾空白、HTML 解码、控制字符被删除，返回 `A&B`
    """
    assert algorithm_modules.utils.clean_str("  A&amp;\nB\x00  ") == "A&B"


def test_messages_alternate_user_and_assistant_roles(algorithm_modules):
    """
    Test Item 测试项：`pack_user_ass_to_openai_messages`
    Test Type：状态序列测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：无
    Input 输入：三条消息 `q1,a1,q2`
    Procedure 操作步骤：调用打包函数并提取 role
    Output 预期结果：role 严格为 `user, assistant, user`，内容顺序不变
    """
    messages = algorithm_modules.utils.pack_user_ass_to_openai_messages(
        "q1", "a1", "q2"
    )

    assert messages == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
    ]


def test_embedding_func_converts_positional_texts_to_keywords(algorithm_modules):
    """
    Test Item 测试项：`EmbeddingFunc.__call__`
    Test Type：接口契约测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：使用记录参数的异步 fake embedding
    Input 输入：位置参数 `['a','b']`，模型名 `fake-model`
    Procedure 操作步骤：通过 `asyncio.run` 调用 wrapper，检查 fake 收到的关键字参数
    Output 预期结果：`texts` 和 `model_name` 被正确传递，返回值原样转发
    """
    received = {}

    async def fake_embedding(**kwargs):
        received.update(kwargs)
        return [1, 2]

    embedding = algorithm_modules.utils.EmbeddingFunc(
        embedding_dim=2,
        max_token_size=10,
        model_name="fake-model",
        func=fake_embedding,
    )

    result = asyncio.run(embedding(["a", "b"]))

    assert result == [1, 2]
    assert received == {"texts": ["a", "b"], "model_name": "fake-model"}


def test_async_limit_never_exceeds_configured_capacity(algorithm_modules):
    """
    Test Item 测试项：`limit_async_func_call` 正常并发限制
    Test Type：并发测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：限制容量为 2，创建 6 个任务
    Input 输入：任务内部短暂 `await`
    Procedure 操作步骤：并发运行全部任务并记录最大活跃数
    Output 预期结果：所有任务完成，最大活跃数不超过 2
    """
    async def scenario():
        active = 0
        maximum = 0

        @algorithm_modules.utils.limit_async_func_call(2, waitting_time=0.0001)
        async def operation(value):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0.005)
            active -= 1
            return value

        results = await asyncio.gather(*(operation(value) for value in range(6)))
        return results, maximum

    results, maximum = asyncio.run(scenario())

    assert results == list(range(6))
    assert maximum <= 2


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


def test_async_limit_rejects_zero_capacity(algorithm_modules):
    """
    Test Item 测试项：`limit_async_func_call` 容量参数校验
    Test Type：边界值分析
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：准备一个异步函数
    Input 输入：`max_size=0`
    Procedure 操作步骤：用零容量装饰函数，不真正发起可能无限等待的调用
    Output 预期结果：装饰阶段抛出 `ValueError`
    """
    actual = "configuration accepted"
    try:
        algorithm_modules.utils.limit_async_func_call(0)
    except ValueError:
        actual = "ValueError"

    assert actual == "ValueError"

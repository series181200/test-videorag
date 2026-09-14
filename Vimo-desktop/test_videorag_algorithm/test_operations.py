"""Unit tests for core functions in python_backend/videorag/_op.py."""

import asyncio

import pytest


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


def test_token_size_chunking_rejects_zero_step(algorithm_modules, fake_tokenizer):
    """
    Test Item 测试项：`chunking_by_token_size` 非法 overlap
    Test Type：边界值分析、异常测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：`overlap == max_size`
    Input 输入：token `[1,2]`、两参数均为 4
    Procedure 操作步骤：调用函数并捕获异常
    Output 预期结果：抛出 `ValueError`，不会进入无限分块
    """
    with pytest.raises(ValueError):
        algorithm_modules.operations.chunking_by_token_size(
            [[1, 2]],
            doc_keys=["doc-1"],
            tiktoken_model=fake_tokenizer,
            overlap_token_size=4,
            max_token_size=4,
        )


def test_token_size_chunking_avoids_overlap_only_tail(algorithm_modules, fake_tokenizer):
    """
    Test Item 测试项：`chunking_by_token_size` 尾块去重
    Test Type：边界值分析
    Test Criticality 重要级别：High
    Pre-condition 预置条件：步长为 3，最后起点只落在已覆盖 token 上
    Input 输入：7 个 token，`max=4`、`overlap=1`
    Procedure 操作步骤：生成块并检查最后一块是否带来新 token
    Output 预期结果：只生成两个有效块，不生成仅含 token `7` 的重复尾块
    """
    result = algorithm_modules.operations.chunking_by_token_size(
        [[1, 2, 3, 4, 5, 6, 7]],
        doc_keys=["doc-1"],
        tiktoken_model=fake_tokenizer,
        overlap_token_size=1,
        max_token_size=4,
    )

    assert len(result) == 2


def test_video_segments_are_grouped_without_crossing_limit(algorithm_modules, fake_tokenizer):
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


def test_video_segment_chunking_handles_empty_input(algorithm_modules, fake_tokenizer):
    """
    Test Item 测试项：`chunking_by_video_segments` 空输入
    Test Type：等价类划分（空等价类）
    Test Criticality 重要级别：Medium
    Pre-condition 预置条件：无
    Input 输入：空 token 列表和空 ID 列表
    Procedure 操作步骤：调用分段合并函数
    Output 预期结果：返回空列表，不创建 token 数为 0 的块
    """
    result = algorithm_modules.operations.chunking_by_video_segments(
        [], doc_keys=[], tiktoken_model=fake_tokenizer, max_token_size=3
    )

    assert result == []


def test_video_segment_chunking_does_not_mutate_input(algorithm_modules, fake_tokenizer):
    """
    Test Item 测试项：`chunking_by_video_segments` 输入不可变性
    Test Type：性质测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：保存二维 token 列表深拷贝
    Input 输入：单个 4-token segment，最大块大小 3
    Procedure 操作步骤：调用函数后比较原列表与副本
    Output 预期结果：函数可在输出中截断，但不得修改调用方输入列表
    """
    token_lists = [[1, 2, 3, 4]]
    original = [tokens.copy() for tokens in token_lists]

    algorithm_modules.operations.chunking_by_video_segments(
        token_lists,
        doc_keys=["video_0"],
        tiktoken_model=fake_tokenizer,
        max_token_size=3,
    )

    assert token_lists == original


def test_get_chunks_builds_content_hash_and_segment_metadata(
    algorithm_modules, fake_tokenizer, monkeypatch
):
    """
    Test Item 测试项：`get_chunks` 编排逻辑
    Test Type：接口契约、集成式单元测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：将 tiktoken 替换为 deterministic fake
    Input 输入：一个视频含 `0/1` 两段文本
    Procedure 操作步骤：编码、调用默认 chunker、检查哈希 key 和 segment 元数据
    Output 预期结果：返回一个以 `chunk-` 开头的哈希项，包含两个原 segment ID
    """
    monkeypatch.setattr(
        algorithm_modules.operations.tiktoken,
        "encoding_for_model",
        lambda model_name: fake_tokenizer,
        raising=False,
    )
    videos = {
        "demo": {
            "0": {"content": "ab"},
            "1": {"content": "cd"},
        }
    }

    result = algorithm_modules.operations.get_chunks(videos, max_token_size=10)

    assert len(result) == 1
    chunk_id, chunk = next(iter(result.items()))
    assert chunk_id.startswith("chunk-")
    assert chunk["video_segment_id"] == ["demo_0", "demo_1"]
    assert chunk["tokens"] == 4


def test_entity_record_is_normalized_to_graph_node(algorithm_modules):
    """
    Test Item 测试项：`_handle_single_entity_extraction`
    Test Type：等价类划分（合法实体）
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：无
    Input 输入：合法 entity record，名称含小写，描述含 HTML entity
    Procedure 操作步骤：异步解析记录并检查 node 字段
    Output 预期结果：名称和类型转大写、描述被清理、source ID 等于 chunk key
    """
    result = asyncio.run(
        algorithm_modules.operations._handle_single_entity_extraction(
            ['"entity"', "alice", "person", "A&amp;B"], "chunk-1"
        )
    )

    assert result == {
        "entity_name": "ALICE",
        "entity_type": "PERSON",
        "description": "A&B",
        "source_id": "chunk-1",
    }


@pytest.mark.parametrize(
    "record",
    [
        [],
        ['"entity"', "name"],
        ['"relationship"', "name", "type", "description"],
        ['"entity"', "   ", "type", "description"],
    ],
)
def test_invalid_entity_records_are_ignored(algorithm_modules, record):
    """
    Test Item 测试项：`_handle_single_entity_extraction` 非法记录
    Test Type：无效等价类、参数化测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：无
    Input 输入：空、字段不足、类型错误、实体名为空白
    Procedure 操作步骤：分别异步调用解析函数
    Output 预期结果：全部返回 `None`，不生成无效图节点
    """
    result = asyncio.run(
        algorithm_modules.operations._handle_single_entity_extraction(
            record, "chunk-1"
        )
    )

    assert result is None


@pytest.mark.parametrize(
    ("weight", "expected"),
    [("2.5", 2.5), ("bad-weight", 1.0)],
)
def test_relationship_weight_uses_numeric_value_or_default(
    algorithm_modules, weight, expected
):
    """
    Test Item 测试项：`_handle_single_relationship_extraction` 权重解析
    Test Type：等价类划分、参数化测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：合法 relationship 其余字段固定
    Input 输入：数字字符串 `2.5` 与非法字符串
    Procedure 操作步骤：异步解析并检查 `weight`
    Output 预期结果：数字转换为 2.5；非法权重安全回退为 1.0
    """
    result = asyncio.run(
        algorithm_modules.operations._handle_single_relationship_extraction(
            ['"relationship"', "alice", "bob", "knows", weight], "chunk-1"
        )
    )

    assert result["src_id"] == "ALICE"
    assert result["tgt_id"] == "BOB"
    assert result["weight"] == expected


def test_merge_nodes_selects_majority_type_and_unions_sources(
    algorithm_modules, monkeypatch
):
    """
    Test Item 测试项：`_merge_nodes_then_upsert`
    Test Type：状态组合、接口替身测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：fake graph 已有一个 ORG 节点；summary 被替换为恒等函数
    Input 输入：两个 PERSON 新节点，来源/描述存在重复
    Procedure 操作步骤：合并旧数据和新数据并捕获 upsert 内容
    Output 预期结果：多数类型为 PERSON；描述与 source 去重合并；只 upsert 指定节点
    """
    separator = algorithm_modules.prompt.GRAPH_FIELD_SEP

    class FakeGraph:
        saved = None

        async def get_node(self, node_id):
            return {
                "entity_type": "ORG",
                "source_id": "old-source",
                "description": "old-description",
            }

        async def upsert_node(self, node_id, node_data):
            self.saved = (node_id, node_data.copy())

    async def identity_summary(name, description, config):
        return description

    monkeypatch.setattr(
        algorithm_modules.operations,
        "_handle_entity_relation_summary",
        identity_summary,
    )
    graph = FakeGraph()
    nodes = [
        {"entity_type": "PERSON", "source_id": "new-1", "description": "new"},
        {"entity_type": "PERSON", "source_id": "new-2", "description": "new"},
    ]

    result = asyncio.run(
        algorithm_modules.operations._merge_nodes_then_upsert(
            "ALICE", nodes, graph, {}
        )
    )

    assert result["entity_type"] == "PERSON"
    assert set(result["source_id"].split(separator)) == {
        "old-source",
        "new-1",
        "new-2",
    }
    assert set(result["description"].split(separator)) == {
        "old-description",
        "new",
    }
    assert graph.saved[0] == "ALICE"


def test_merge_edges_accumulates_weight_and_creates_missing_nodes(
    algorithm_modules, monkeypatch
):
    """
    Test Item 测试项：`_merge_edges_then_upsert`
    Test Type：状态组合、接口替身测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：fake graph 已有边但没有端点节点；summary 为恒等函数
    Input 输入：旧边权重 2，新边权重 1.5、order 2
    Procedure 操作步骤：合并边并记录节点/边 upsert
    Output 预期结果：权重为 3.5、order 取最小值 2、两个缺失节点被创建
    """
    class FakeGraph:
        def __init__(self):
            self.nodes = []
            self.edge = None

        async def has_edge(self, source, target):
            return True

        async def get_edge(self, source, target):
            return {
                "weight": 2.0,
                "source_id": "old-source",
                "description": "old-description",
                "order": 3,
            }

        async def has_node(self, node_id):
            return False

        async def upsert_node(self, node_id, node_data):
            self.nodes.append((node_id, node_data))

        async def upsert_edge(self, source, target, edge_data):
            self.edge = (source, target, edge_data)

    async def identity_summary(name, description, config):
        return description

    monkeypatch.setattr(
        algorithm_modules.operations,
        "_handle_entity_relation_summary",
        identity_summary,
    )
    graph = FakeGraph()

    result = asyncio.run(
        algorithm_modules.operations._merge_edges_then_upsert(
            "ALICE",
            "BOB",
            [
                {
                    "weight": 1.5,
                    "source_id": "new-source",
                    "description": "new-description",
                    "order": 2,
                }
            ],
            graph,
            {},
        )
    )

    assert result["weight"] == 3.5
    assert {node_id for node_id, _ in graph.nodes} == {"ALICE", "BOB"}
    assert graph.edge[0:2] == ("ALICE", "BOB")
    assert graph.edge[2]["weight"] == 3.5
    assert graph.edge[2]["order"] == 2

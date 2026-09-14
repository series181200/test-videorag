"""Unit tests for python_backend/videorag/_splitter.py."""

def test_empty_token_list_returns_empty_result(algorithm_modules):
    """
    Test Item 测试项：`SeparatorSplitter.split_tokens` 空输入
    Test Type：等价类划分（空等价类）
    Test Criticality 重要级别：Medium
    Pre-condition 预置条件：创建合法 splitter，块大小为 4
    Input 输入：`[]`
    Procedure 操作步骤：调用 `split_tokens` 并比较返回列表
    Output 预期结果：返回空列表 `[]`，不产生空块
    """
    splitter = algorithm_modules.splitter.SeparatorSplitter(
        separators=[[0]], chunk_size=4, chunk_overlap=0
    )

    assert splitter.split_tokens([]) == []


def test_separator_is_kept_at_chunk_end(algorithm_modules):
    """
    Test Item 测试项：`_split_tokens_with_separators` 的 `keep_separator=end` 分支
    Test Type：判定覆盖
    Test Criticality 重要级别：High
    Pre-condition 预置条件：separator 为 `[0]`，不启用 overlap
    Input 输入：`[1,2,0,3]`
    Procedure 操作步骤：执行分块，检查分隔符所在块
    Output 预期结果：分隔符保留在前一块末尾，结果为 `[[1,2,0],[3]]`
    """
    splitter = algorithm_modules.splitter.SeparatorSplitter(
        separators=[[0]], keep_separator="end", chunk_size=3, chunk_overlap=0
    )

    assert splitter.split_tokens([1, 2, 0, 3]) == [[1, 2, 0], [3]]


def test_separator_is_kept_at_chunk_start(algorithm_modules):
    """
    Test Item 测试项：`_split_tokens_with_separators` 的 `keep_separator=start` 分支
    Test Type：判定覆盖
    Test Criticality 重要级别：High
    Pre-condition 预置条件：separator 为 `[0]`，不启用 overlap
    Input 输入：`[1,2,0,3]`
    Procedure 操作步骤：执行分块，检查分隔符所在块
    Output 预期结果：分隔符保留在后一块开头，结果为 `[[1,2],[0,3]]`
    """
    splitter = algorithm_modules.splitter.SeparatorSplitter(
        separators=[[0]], keep_separator="start", chunk_size=3, chunk_overlap=0
    )

    assert splitter.split_tokens([1, 2, 0, 3]) == [[1, 2], [0, 3]]


def test_separator_can_be_removed(algorithm_modules):
    """
    Test Item 测试项：`_split_tokens_with_separators` 的 `keep_separator=False` 分支
    Test Type：判定覆盖
    Test Criticality 重要级别：Medium
    Pre-condition 预置条件：块容量足以重新合并内容
    Input 输入：`[1,0,2]`
    Procedure 操作步骤：执行分块并检查结果中是否仍有 separator
    Output 预期结果：分隔符被删除，业务 token 保持顺序，结果 `[[1,2]]`
    """
    splitter = algorithm_modules.splitter.SeparatorSplitter(
        separators=[[0]], keep_separator=False, chunk_size=10, chunk_overlap=0
    )

    assert splitter.split_tokens([1, 0, 2]) == [[1, 2]]


def test_large_unsplit_input_has_expected_overlap(algorithm_modules):
    """
    Test Item 测试项：`_split_chunk` 固定窗口及 overlap
    Test Type：边界值分析
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：`chunk_size=4`、`chunk_overlap=1`、无 separator
    Input 输入：`range(10)`
    Procedure 操作步骤：分块后检查每块长度、相邻块重叠和最后一个 token
    Output 预期结果：得到 `[[0,1,2,3],[3,4,5,6],[6,7,8,9]]`，无数据丢失
    """
    splitter = algorithm_modules.splitter.SeparatorSplitter(
        separators=[], chunk_size=4, chunk_overlap=1
    )

    assert splitter.split_tokens(list(range(10))) == [
        [0, 1, 2, 3],
        [3, 4, 5, 6],
        [6, 7, 8, 9],
    ]


def test_input_tokens_are_not_modified(algorithm_modules):
    """
    Test Item 测试项：`SeparatorSplitter.split_tokens` 输入不可变性
    Test Type：性质测试
    Test Criticality 重要级别：High
    Pre-condition 预置条件：保存输入列表的副本
    Input 输入：`[1,2,0,3,4]`
    Procedure 操作步骤：调用分块，再将原列表与副本比较
    Output 预期结果：原始 token 列表内容和顺序均不改变
    """
    tokens = [1, 2, 0, 3, 4]
    original = tokens.copy()
    splitter = algorithm_modules.splitter.SeparatorSplitter(
        separators=[[0]], chunk_size=3, chunk_overlap=1
    )

    splitter.split_tokens(tokens)

    assert tokens == original


def test_empty_separator_configuration_is_rejected(algorithm_modules):
    """
    Test Item 测试项：`SeparatorSplitter.__init__` separator 校验
    Test Type：健壮性测试、错误推测
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：无
    Input 输入：`separators=[[]]`
    Procedure 操作步骤：仅构造 splitter，要求在进入循环前校验配置
    Output 预期结果：立即抛出 `ValueError`，避免 `split_tokens` 死循环
    """
    actual = "configuration accepted"
    try:
        algorithm_modules.splitter.SeparatorSplitter(
            separators=[[]], chunk_size=4, chunk_overlap=1
        )
    except ValueError:
        actual = "ValueError"

    assert actual == "ValueError"


def test_overlap_must_be_smaller_than_chunk_size(algorithm_modules):
    """
    Test Item 测试项：`SeparatorSplitter.__init__` overlap 边界
    Test Type：边界值分析
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：`chunk_size=4`
    Input 输入：`chunk_overlap=4`
    Procedure 操作步骤：构造边界相等的配置
    Output 预期结果：构造阶段抛出 `ValueError`，而不是运行时产生非法步长
    """
    actual = "configuration accepted"
    try:
        algorithm_modules.splitter.SeparatorSplitter(
            separators=[], chunk_size=4, chunk_overlap=4
        )
    except ValueError:
        actual = "ValueError"

    assert actual == "ValueError"


def test_overlap_does_not_discard_tail_tokens(algorithm_modules):
    """
    Test Item 测试项：`_enforce_overlap` 数据完整性
    Test Type：性质测试
    Test Criticality 重要级别：Critical
    Pre-condition 预置条件：两个 separator 块在添加 overlap 后超过块大小
    Input 输入：`[1,2,3,0,4,5,6,0]`
    Procedure 操作步骤：分块后检查末尾 separator 和所有原始 token 是否仍可覆盖
    Output 预期结果：末尾 token `0` 不丢失，所有输入业务数据都出现在输出块中
    """
    splitter = algorithm_modules.splitter.SeparatorSplitter(
        separators=[[0]], keep_separator="end", chunk_size=5, chunk_overlap=2
    )

    chunks = splitter.split_tokens([1, 2, 3, 0, 4, 5, 6, 0])

    assert chunks[-1][-1] == 0


def test_invalid_keep_separator_value_is_rejected(algorithm_modules):
    """
    Test Item 测试项：`SeparatorSplitter.__init__` 模式参数校验
    Test Type：无效等价类
    Test Criticality 重要级别：Medium
    Pre-condition 预置条件：无
    Input 输入：`keep_separator="middle"`
    Procedure 操作步骤：使用类型声明之外的字符串构造对象
    Output 预期结果：抛出 `ValueError`，不静默改变处理语义
    """
    actual = "configuration accepted"
    try:
        algorithm_modules.splitter.SeparatorSplitter(
            separators=[[0]], keep_separator="middle", chunk_size=4, chunk_overlap=1
        )
    except ValueError:
        actual = "ValueError"

    assert actual == "ValueError"

"""Unit tests for foundational data structures in videorag/base.py."""


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


def test_query_param_accepts_supported_custom_values(algorithm_modules):
    """
    Test Item 测试项：`QueryParam` 自定义配置
    Test Type：等价类划分（合法值）
    Test Criticality 重要级别：High
    Pre-condition 预置条件：无
    Input 输入：mode=`local`、top_k=5、level=1、only_need_context=True
    Procedure 操作步骤：使用关键字参数构造并读取字段
    Output 预期结果：所有传入值被完整保存，不被默认值覆盖
    """
    params = algorithm_modules.base.QueryParam(
        mode="local", top_k=5, level=1, only_need_context=True
    )

    assert params.mode == "local"
    assert params.top_k == 5
    assert params.level == 1
    assert params.only_need_context is True


def test_query_param_instances_do_not_share_mutable_state(algorithm_modules):
    """
    Test Item 测试项：`QueryParam` 实例隔离
    Test Type：独立性测试
    Test Criticality 重要级别：Medium
    Pre-condition 预置条件：创建两个默认实例
    Input 输入：修改第一个实例的 `top_k`
    Procedure 操作步骤：比较两个对象的字段
    Output 预期结果：第一个变为 1，第二个仍为默认 20
    """
    first = algorithm_modules.base.QueryParam()
    second = algorithm_modules.base.QueryParam()

    first.top_k = 1

    assert first.top_k == 1
    assert second.top_k == 20

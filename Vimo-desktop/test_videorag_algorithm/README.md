# VideoRAG 算法单元测试

本目录只测试 `python_backend/videorag/` 中的算法、基础数据结构和本地 JSON 存储，不启动 Electron、Flask、真实大模型、GPU、Neo4j 或向量数据库服务。

## 测试文件

| 文件 | 覆盖对象 |
|---|---|
| `test_splitter.py` | `SeparatorSplitter` 的分隔符、块大小、重叠与非法配置 |
| `test_utils.py` | JSON 提取、字符串清理、哈希、token 截断、异步限流 |
| `test_operations.py` | `_op.py` 的 token 分块、视频段合并、实体和关系解析 |
| `test_json_storage.py` | `JsonKVStorage` 的 CRUD 与磁盘持久化契约 |
| `test_base.py` | `QueryParam` 默认值、自定义值和实例隔离 |
| `conftest.py` | 从源码隔离加载算法模块，并替代测试不需要的外部模型依赖 |

每条测试函数的 docstring 都包含以下课程用例字段：Test Item、Test Type、Test Criticality、Pre-condition、Input、Procedure 和 Output。

## 安装与执行

请先激活 Vimo 使用的 Python/Conda 环境，然后在 `Vimo-desktop` 根目录运行：

```powershell
python -m pip install -r test_videorag_algorithm/requirements-test.txt
python -m pytest -c test_videorag_algorithm/pytest.ini test_videorag_algorithm -v
```

只运行某一模块：

```powershell
python -m pytest test_videorag_algorithm/test_splitter.py -v
```

生成 JUnit XML 课程报告：

```powershell
python -m pytest -c test_videorag_algorithm/pytest.ini test_videorag_algorithm --junitxml=test_videorag_algorithm/report.xml
```

## 结果判读

- `PASSED`：实际输出与根据功能规格设计的预期输出相同。
- `FAILED`：实际输出与预期输出不同，测试在主动执行中发现了潜在缺陷。
- `ERROR`：测试环境、fixture 或脚本自身出错，需要先排除环境问题，不能直接认定为被测代码缺陷。

缺陷测试不使用 `xfail`、`skip` 或预先登记的漏洞标记，全部作为普通黑盒断言执行。当前基线执行结果为 `47 passed, 8 failed`；8 个失败项是通过预期值与实际值不一致主动暴露出来的。修复算法后，对应用例应自然从 `FAILED` 变成 `PASSED`，测试脚本无需更换标记。

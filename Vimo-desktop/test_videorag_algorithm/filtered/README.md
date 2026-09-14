# VideoRAG 算法层日常核心测试集

本目录保留从完整算法测试中筛选出的 7 条日常核心用例，覆盖默认查询、模型 JSON 解析、Token 边界、视频分段、持久化和异步异常恢复。

在 `Vimo-desktop` 根目录运行：

```powershell
python -m pytest -c test_videorag_algorithm/filtered/pytest.ini test_videorag_algorithm/filtered -v
```

当前源码基线为 `6 passed, 1 failed`。失败项用于主动暴露模型调用异常后并发容量未释放的问题，不使用 `xfail` 或 `skip`。


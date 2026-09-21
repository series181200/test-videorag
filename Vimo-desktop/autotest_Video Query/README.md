# 视频内容查询测试 VQ

按最新约定，每个业务 ID 只选一个代表性样例，共 **4 条测试：pytest 2 条、Vitest 2 条**。保留业务逻辑断言，不再把同一 ID 拆成多个参数、多个框架的必过检查。

一个样例中的多步操作和多个必要断言不额外计数。业务源码未修改。

## 当前测试清单

| ID | 唯一代表样例 | 核心判定 | 框架 |
| --- | --- | --- | --- |
| TC-VQ-001 | 向查询接口提交三个空格的问题 | 请求被拒绝，不调用查询任务调度 | pytest |
| TC-VQ-002 | 向不存在的会话提交正常问题 | 请求被拒绝，不创建会话目录或查询进程 | pytest |
| TC-VQ-003 | 查询出现模型超时错误，随后重新提问 | 结束等待并反馈错误；历史消息保留，重试后收到新答案 | Vitest |
| TC-VQ-004 | A 尚未回答时提交 B，A 完成后再次提交 B | 忙碌时不重复下发；两次问题与答案保持对应 | Vitest |

VQ-001、002 接受合理的 4xx 错误，不限定只能返回 400、404 或 409；仍不能把 500、虚假成功或创建了无效任务视为正确行为。

## 本轮范围与旧版区别

- VQ-001 只选全空格输入，移出其他空白组合和正常输入对照；真实路由执行，调度方法作为依赖替身，用于判断入口是否拦截。
- VQ-002 只选不存在的会话，使用真实路由、管理器和临时文件操作，移出“未索引”“正在索引”和正常启动对照。
- VQ-003、004 只保留真实 `useChat` 和消息处理逻辑的代表样例。它们通过表示查询交互正确，不表示后端资源释放、并发进程保护已验证通过。
- 原先被 Windows 状态文件更新问题阻断的 Python 恢复/并发检查已移出本轮，原始报告继续保留。该状态写入问题没有被修复，也没有替换真实写入来制造通过。
- 旧版 22 个检查与本轮 4 个样例覆盖范围不同，不能将通过率变化当作软件质量提升。

## 一键运行

在仓库根目录执行：

```powershell
python Vimo-desktop/test_video_query/run_tests.py
```

也可执行 `npm.cmd test --prefix Vimo-desktop/test_video_query`。运行器在独立进程中分别执行 pytest 与 Vitest，即使前者失败仍执行后者。

依赖缺失时：

```powershell
python -m pip install -r Vimo-desktop/test_video_query/requirements-test.txt
npm.cmd install --prefix Vimo-desktop/test_video_query
```

优先使用本目录 JavaScript 依赖，否则复用 `test_renderer/node_modules`。Vitest 固定 2.1.9；React、React DOM、Router 和 Testing Library 必须从同一依赖目录解析。

单独排查 Python：

```powershell
python -m pytest -c Vimo-desktop/test_video_query/pytest.ini Vimo-desktop/test_video_query -q
```

## 当前文件与隔离边界

- `test_query_validation.py`：VQ-001。
- `test_query_readiness.py`：VQ-002。
- `query_recovery.test.tsx`：VQ-003。
- `query_submission.test.tsx`：VQ-004。
- `conftest.py`：显式导入并核对真实 `python_backend/videorag_api.py`；使用临时目录和可控进程替身，不导入旧测试中的 API 副本。
- `renderer_support.tsx`：真实 hook 与消息处理代码；上下文、索引元数据、IPC 和定时器为受控依赖。
- `pytest.ini`、`vitest.config.ts`：收集本轮测试。
- `run_tests.py`：分别检查 pytest/Vitest 的 ID 映射，每个 ID 恰好一条。

测试不启动真实模型进程，不调用付费模型。Vitest 判断的是 hook 返回的等待状态和消息，不声称覆盖整个 App、真实按钮或 IPC 到 Python 的联调。

## 结果与证据

每次执行生成独立 `results/<UTC时间戳>-<进程号>/`，保存环境与源码哈希、原始 pytest XML、Vitest JSON、日志、业务汇总 JSON/CSV 和合并 JUnit XML。

退出码 0 为全部通过，1 为存在失败，2 为依赖、收集或运行异常。失效用例不会被 skip/xfail；修改测试数量时必须同步修改运行器的 `EXPECTED`。

本轮样例调整和最新结果见 [精简记录](evidence/simplification.md)。[旧版实施记录](evidence/implementation.md) 及其 22 条检查报告仅作历史追踪。

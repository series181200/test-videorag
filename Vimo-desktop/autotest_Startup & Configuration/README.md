# 启动与配置测试 SC

按最新约定，每个业务 ID 只保留一个代表性测试样例，共 **5 条 Vitest 测试**。重点验证功能和逻辑结果，不再穷举参数，不要求固定错误文案、精确端口扫描次数或 60 秒业务时限。

一个样例可以包含“失败 → 修复条件 → 重试”的连续操作，以及多个必要断言，但只计一条测试。业务源码未修改。

## 当前测试清单

| ID | 唯一代表样例 | 核心判定 | 脚本 |
| --- | --- | --- | --- |
| TC-SC-001 | 打包目录缺少后端可执行文件 | 启动失败，未创建后端进程 | startup.test.ts |
| TC-SC-002 | 启动时后端短暂不可达，随后服务恢复 | 恢复前不误报成功，恢复后能够连接成功 | startup.test.ts |
| TC-SC-003 | 已存在的 bootstrap JSON 损坏，保存正确配置后重试 | 错误配置不能初始化，修复后可以重新初始化 | configuration.test.ts |
| TC-SC-004 | 使用 sk- 开头但无效的假密钥 | 不能只凭前缀返回验证成功 | api_key_validation.test.ts |
| TC-SC-005 | ImageBind 模型文件缺失，恢复文件后重试 | 缺失时初始化失败，恢复后初始化成功 | configuration.test.ts |

样例按部署阻断、配置可恢复性和认证逻辑选择，不因某条失败就将它跳过或更改为预期失败。错误文本只要求能够表达失败，不限定固定字符串。

## 本轮范围与旧版区别

- SC-002 本轮只验证短暂断连后的自动重连，不再验证长期不可达后的有限次数退出，也不宣称该问题已经修复。测试中推进虚拟时间只为驱动调度；有保护循环避免脚本永久等待。
- SC-003 只选损坏 JSON，不再分别执行多个必填字段缺失组合。
- SC-004 只选无效密钥，移出合法密钥对照、网络超时和请求次数检查。当前业务代码没有认证请求；测试准备的 401 是依赖替身，不是真实服务响应。
- SC-005 只选模型缺失，不再把目录不可写作为本轮必测样例。旧版发现的写权限问题仍保留在历史报告中。
- 旧版 14 个检查的报告是历史记录，不能与当前 5 个代表样例直接比较通过率。范围缩小不是业务缺陷已修复。

## 一键运行

在仓库根目录执行：

```powershell
node Vimo-desktop/test_startup_configuration/run_tests.cjs
```

或：

```powershell
npm.cmd test --prefix Vimo-desktop/test_startup_configuration
```

运行器优先使用本目录依赖，否则复用现有 `test_communication/node_modules` 中的 Vitest 2.1.9。两处都未安装时：

```powershell
npm.cmd install --prefix Vimo-desktop/test_startup_configuration
```

## 代码与测试边界

- `startup.test.ts`：SC-001、SC-002。
- `configuration.test.ts`：SC-003、SC-005。
- `api_key_validation.test.ts`：SC-004。
- `support.ts`：隔离 Electron、HTTP、文件系统和进程，恢复环境变量、模块状态及定时器。
- `vitest.config.ts`：Node 环境，只收集本目录测试。
- `run_tests.cjs`：检查每个 ID 恰好收集一条，输出结果及版本证据。

执行真实的 `src/main/handlers/settings.ts` 和 `videorag-handlers.ts`，不复制业务实现。依赖替身模拟缺失文件、损坏配置和服务恢复，不使用真实密钥、不启动真实后端，也不修改用户文件权限。

当前没有 Python 测试，因此不创建空的 pytest 配置。未来若测试 Python，使用 pytest。

## 结果与证据

每轮在 `results/<UTC时间戳>-<进程号>/` 保存：

- `manifest.json`：源码/测试哈希、Git 版本与执行环境。
- `vitest.json`、`console.txt`：原始结果和日志。
- `summary.json`、`summary.csv`：5 个业务 ID 的结果。
- `junit.xml`：由原始 JSON 生成的 JUnit 报告。

退出码 0 为全部通过，1 为存在失败，2 为收集或运行错误。不使用 skip/xfail 隐藏失败。

本轮调整和最新结果见 [精简记录](evidence/simplification.md)。[旧版实施记录](evidence/implementation.md) 及其 14 条检查报告仅作历史追踪。

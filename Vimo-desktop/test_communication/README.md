# Vimo 通信层单元测试

本目录测试 Vimo Desktop 的第二层通信链路，不启动 Electron 窗口，也不启动真实 Python/VideoRAG 服务：

```text
renderer -> src/preload/index.ts -> Electron IPC -> src/main/handlers -> Python HTTP API
```

测试通过 mock 隔离 Electron、文件系统和 HTTP，重点检查 IPC 通道、参数顺序、返回值、异常转换、输入校验和安全边界。

## 安装与运行

在 `Vimo-desktop` 根目录执行：

```powershell
npm.cmd install --prefix test_communication
npm.cmd test --prefix test_communication
```

显示每条用例名称：

```powershell
npm.cmd run test:verbose --prefix test_communication
```

只运行一个测试文件：

```powershell
npm.cmd test --prefix test_communication -- test_communication/preload.test.ts
```

生成 JUnit XML 课程测试报告：

```powershell
npm.cmd run test:report --prefix test_communication
```

## 文件说明

- `preload.test.ts`：renderer 到 IPC 的 API 暴露、通道映射及事件边界。
- `file-handlers.test.ts`：文件类 IPC Handler 的正常、取消和异常分支。
- `settings-handlers.test.ts`：配置通信、默认值、合并与 API Key 参数校验。
- `chat-session-handlers.test.ts`：会话 IPC 的注册、持久化、排序和参数安全。
- `videorag-handlers.test.ts`：main 到 Python API 的 URL、方法、请求体、超时和错误映射。

每条测试前都使用七行字段说明 Test Item、Test Type、Test Criticality、Pre-condition、Input、Procedure 和 Output。缺陷测试全部使用普通断言，不使用 `skip`、`todo` 或预期失败标记；当实现与需求不一致时，Vitest 会直接报告 `FAILED` 并展示预期值和实际值。

## 当前测试基线

当前源码的实际执行结果为：

```text
Test Files  5 failed (5)
Tests       10 failed | 35 passed (45)
```

10 个失败用例主动暴露了以下预期与实际不一致：

1. renderer 使用并声明了 `window.api.invoke`，preload 实际未暴露该函数。
2. 下载事件把原始 Electron event 直接传给 renderer，没有隔离特权对象。
3. 只有前缀、没有密钥主体的 `sk-` 被判定为合法 API Key。
4. Windows 视频路径没有正确提取文件名。
5. 所有视频的 `stat` 均失败时，接口仍返回 `success=true` 和空数组。
6. 会话 ID 包含路径穿越字符时仍会进入文件写入逻辑。
7. 未知的会话排序 operation 被当作合法操作写入。
8. 空查询仍被发送给 Python API。
9. chatId 未经 URL 编码便被拼入 Python API 路径。
10. status type 未经 URL 编码便被拼入查询字符串。

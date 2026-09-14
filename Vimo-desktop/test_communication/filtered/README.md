# Vimo 通信层日常核心测试集

本目录保留从完整通信测试中筛选出的 8 条日常核心用例，按应用启动、配置加载、视频选择与上传、会话保存和后端异常返回等真实用户链路组织。

先在 `Vimo-desktop` 根目录安装通信测试依赖：

```powershell
npm.cmd install --prefix test_communication
```

运行筛选后的测试：

```powershell
test_communication\node_modules\.bin\vitest.cmd run --config test_communication\filtered\vitest.config.ts --reporter=verbose
```

当前源码基线为 `6 passed, 2 failed`。失败项用于主动暴露 preload 缺少 `api.invoke` 和 Windows 视频文件名提取错误，不使用 `skip` 或预期失败标记。


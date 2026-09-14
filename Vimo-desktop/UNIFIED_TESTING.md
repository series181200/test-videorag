# Vimo 四层统一测试

统一入口会依次执行：

1. `test_renderer`：全部 Vitest + jsdom 前端用例。
2. `test_communication/filtered`：筛选后的 Vitest 通信用例。
3. `test_videorag_api`：全部 pytest API 用例。
4. `test_videorag_algorithm/filtered`：筛选后的 pytest 算法用例。

每条用例在终端输出测试层级、测试接口或函数、`OK/NG` 和发现的问题。某一层失败后，后续层仍会继续运行。

四个测试层只使用两种框架：TypeScript 使用 Vitest，Python 使用 pytest。

## 首次安装依赖

在 `Vimo-desktop` 根目录执行：

```powershell
python -m pip install -r requirements-unified-tests.txt
npm.cmd install --prefix test_renderer
npm.cmd install --prefix test_communication
```

如果终端无法直接识别 `python`，请把上面第一条中的 `python` 换成实际解释器路径；例如本机可用
`C:\ProgramData\miniconda3\python.exe`。批处理启动时会依次尝试当前 Conda 环境、PATH 中的
Python、该 Miniconda 路径和 Windows `py` 启动器。

## 一键运行

双击：

```text
run_all_layer_tests.bat
```

或者在终端执行：

```powershell
python run_all_layer_tests.py
```

如果需要指定 Conda 环境，可以先设置：

```powershell
$env:VIMO_TEST_PYTHON = "D:\develop\conda_envs\your_env\python.exe"
.\run_all_layer_tests.bat
```

renderer 测试直接加载 React 源码并在 jsdom 中执行，不再依赖 Playwright、Chromium 或根目录的 pnpm `node_modules`。框架或 Python 依赖缺失时，该层用例会显示为 NG，并明确标记为测试环境问题而不是业务漏洞。

## 分层单独运行

```powershell
test_renderer\node_modules\.bin\vitest.cmd run --config test_renderer\vitest.config.ts
test_communication\node_modules\.bin\vitest.cmd run --config test_communication\filtered\vitest.config.ts
python -m pytest -c test_videorag_api\pytest.ini test_videorag_api\tests
python -m pytest -c test_videorag_algorithm\filtered\pytest.ini test_videorag_algorithm\filtered
```

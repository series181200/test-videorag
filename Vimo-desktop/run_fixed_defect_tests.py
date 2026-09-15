"""Rerun only TC-API-009, TC-API-011, TC-COM-002 and TC-ALG-007."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class RegressionCase:
    case_id: str
    layer: str
    target: str
    fixed_finding: str
    command: tuple[str, ...]


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def run_case(case: RegressionCase, temp_dir: Path) -> tuple[bool, str]:
    command = [part.replace("{TEMP}", str(temp_dir)) for part in case.command]
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            # The API regression cases must exercise the application module,
            # not only the isolated copy kept by the broader API test suite.
            "VIMO_TEST_PRODUCTION_API": "1",
        }
    )
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
        )
        return completed.returncode == 0, completed.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return False, str(error)


def main() -> int:
    configure_console()
    vitest = ROOT / "test_communication" / "node_modules" / ".bin" / (
        "vitest.cmd" if os.name == "nt" else "vitest"
    )
    if not vitest.exists():
        print("缺少通信层 Vitest，请先执行：npm.cmd install --prefix test_communication")
        return 2

    cases = (
        RegressionCase(
            "TC-API-009",
            "后端与算法通信层",
            "VideoRAGProcessManager.terminate_process",
            "终止会话时索引进程与查询进程均被清理",
            (
                sys.executable,
                "-m",
                "pytest",
                "-c",
                "test_videorag_api/pytest.ini",
                "test_videorag_api/tests/process/test_process.py::test_terminate_session_stops_related_processes",
                "--basetemp={TEMP}/api-009",
                "-q",
            ),
        ),
        RegressionCase(
            "TC-API-011",
            "后端与算法通信层",
            "VideoRAGProcessManager.set_global_config",
            "日志中的 OpenAI 与 DashScope API Key 已脱敏",
            (
                sys.executable,
                "-m",
                "pytest",
                "-c",
                "test_videorag_api/pytest.ini",
                "test_videorag_api/tests/security/test_security.py::test_global_config_does_not_log_api_keys",
                "--basetemp={TEMP}/api-011",
                "-q",
            ),
        ),
        RegressionCase(
            "TC-COM-002",
            "前后端通信层",
            "preload / window.api.invoke",
            "renderer 使用的通用 IPC 调用入口已在运行时暴露",
            (
                str(vitest),
                "run",
                "--config",
                "test_communication/filtered/vitest.config.ts",
                "test_communication/filtered/preload.filtered.ts",
                "-t",
                "provides the generic invoke function declared and used by renderer",
                "--reporter=verbose",
            ),
        ),
        RegressionCase(
            "TC-ALG-007",
            "VideoRAG 算法层",
            "limit_async_func_call",
            "异步调用异常后会释放并发容量，后续任务不再永久等待",
            (
                sys.executable,
                "-m",
                "pytest",
                "-c",
                "test_videorag_algorithm/filtered/pytest.ini",
                "test_videorag_algorithm/filtered/selected_daily_algorithm.py::test_async_limit_releases_capacity_after_exception",
                "--basetemp={TEMP}/alg-007",
                "-q",
            ),
        ),
    )

    results: list[bool] = []
    with tempfile.TemporaryDirectory(prefix=".fixed-defects-", dir=ROOT) as temp_name:
        temp_dir = Path(temp_name)
        for case in cases:
            passed, output = run_case(case, temp_dir)
            results.append(passed)
            status = "OK" if passed else "NG"
            finding = f"缺陷已解决：{case.fixed_finding}" if passed else "缺陷仍存在或测试环境异常"
            print("=" * 88)
            print(f"{case.case_id}  [{status}]")
            print(f"测试层级：{case.layer}")
            print(f"测试接口/函数：{case.target}")
            print(f"测试结论：{finding}")
            if not passed:
                print("失败输出：")
                print(output[-3000:] if output else "测试框架没有返回输出")

    passed_count = sum(results)
    print("=" * 88)
    print(f"四缺陷回归汇总：总数 {len(results)}，OK {passed_count}，NG {len(results) - passed_count}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

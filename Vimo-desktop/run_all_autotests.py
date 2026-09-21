"""Run the four deployment-oriented Vimo autotest suites in one command."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Suite:
    code: str
    name: str
    command: tuple[str, ...]
    timeout: int


@dataclass(frozen=True)
class SuiteResult:
    code: str
    name: str
    status: str
    exit_code: int
    detail: str = ""


def configure_console() -> None:
    """Keep Chinese output readable in Windows terminals and redirected logs."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def build_suites(
    root: Path,
    python_executable: str,
    node_executable: str,
) -> list[Suite]:
    """Build argument-list commands so spaces and ampersands are never shell-parsed."""
    root = Path(root)
    startup = root / "autotest_Startup & Configuration"
    recovery = root / "autotest_State & Recovery"
    indexing = root / "autotest_Video Indexing"
    query = root / "autotest_Video Query"

    return [
        Suite(
            "SC",
            "启动与配置",
            (node_executable, str(startup / "run_tests.cjs")),
            180,
        ),
        Suite(
            "SR",
            "状态与恢复",
            (
                python_executable,
                "-m",
                "pytest",
                "-c",
                str(recovery / "pytest.ini"),
                str(recovery),
                "--basetemp",
                str(root / "output" / "pytest_tmp_state_recovery"),
                "-q",
            ),
            180,
        ),
        Suite(
            "VI",
            "视频索引",
            (
                python_executable,
                "-m",
                "pytest",
                "-c",
                str(indexing / "pytest.ini"),
                str(indexing),
                "--basetemp",
                str(root / "output" / "pytest_tmp_video_indexing"),
                "-q",
            ),
            180,
        ),
        Suite(
            "VQ",
            "视频查询",
            (python_executable, str(query / "run_tests.py")),
            300,
        ),
    ]


def _status_from_exit_code(exit_code: int) -> str:
    if exit_code == 0:
        return "OK"
    if exit_code == 1:
        return "NG"
    return "ERROR"


def run_suites(
    suites: Sequence[Suite],
    *,
    cwd: Path,
) -> tuple[list[SuiteResult], int]:
    """Run every suite sequentially, even if an earlier suite fails."""
    results: list[SuiteResult] = []
    env = dict(
        os.environ,
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        NO_COLOR="1",
    )

    for index, suite in enumerate(suites, start=1):
        print("\n" + "=" * 88, flush=True)
        print(f"[{index}/{len(suites)}] {suite.code} - {suite.name}", flush=True)
        print("=" * 88, flush=True)
        detail = ""
        try:
            completed = subprocess.run(
                list(suite.command),
                cwd=cwd,
                env=env,
                timeout=suite.timeout,
                check=False,
            )
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            exit_code = 124
            detail = f"运行超过 {suite.timeout} 秒，已停止等待"
            print(f"[ERROR] {detail}", file=sys.stderr, flush=True)
        except OSError as error:
            exit_code = 127
            detail = str(error)
            print(f"[ERROR] 无法启动测试：{detail}", file=sys.stderr, flush=True)

        status = _status_from_exit_code(exit_code)
        results.append(
            SuiteResult(suite.code, suite.name, status, exit_code, detail)
        )
        print(f"\n[{suite.code}] {status}（退出码 {exit_code}）", flush=True)

    if any(result.status == "ERROR" for result in results):
        final_exit_code = 2
    elif any(result.status == "NG" for result in results):
        final_exit_code = 1
    else:
        final_exit_code = 0
    return results, final_exit_code


def print_summary(results: Sequence[SuiteResult], final_exit_code: int) -> None:
    print("\n" + "=" * 88)
    print("Vimo 四组自动化测试汇总")
    print("=" * 88)
    for result in results:
        suffix = f"：{result.detail}" if result.detail else ""
        print(f"[{result.status:5}] {result.code} - {result.name}{suffix}")
    print("-" * 88)
    print(
        "最终结果："
        + {0: "OK（全部通过）", 1: "NG（发现测试失败）", 2: "ERROR（存在环境或运行异常）"}[
            final_exit_code
        ]
    )
    print("=" * 88)


def main() -> int:
    configure_console()
    node_executable = shutil.which("node") or "node"
    suites = build_suites(ROOT, sys.executable, node_executable)
    results, exit_code = run_suites(suites, cwd=ROOT)
    print_summary(results, exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

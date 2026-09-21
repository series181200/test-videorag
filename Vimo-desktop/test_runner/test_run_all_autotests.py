"""Behavior tests for the four-suite one-click autotest launcher."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_FILE = PROJECT_ROOT / "run_all_autotests.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("vimo_all_autotests", RUNNER_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load runner: {RUNNER_FILE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_suites_keeps_space_and_ampersand_paths_as_single_arguments(tmp_path):
    """A shell-unsafe project path must still produce four executable commands."""
    runner = load_runner()
    root = tmp_path / "Vimo Desktop & tests"

    suites = runner.build_suites(root, "python-test", "node-test")

    assert [suite.code for suite in suites] == ["SC", "SR", "VI", "VQ"]
    assert suites[0].command == (
        "node-test",
        str(root / "autotest_Startup & Configuration" / "run_tests.cjs"),
    )
    assert str(root / "autotest_State & Recovery" / "pytest.ini") in suites[1].command
    assert str(root / "autotest_Video Indexing") in suites[2].command
    assert suites[3].command == (
        "python-test",
        str(root / "autotest_Video Query" / "run_tests.py"),
    )


def test_run_suites_continues_after_ng_and_returns_one(tmp_path):
    """A product failure in one suite must not prevent later suites from running."""
    runner = load_runner()
    marker = tmp_path / "executed.txt"

    def suite(code: str, exit_code: int):
        program = (
            "from pathlib import Path; import sys; "
            f"p=Path(r'{marker}'); "
            f"p.write_text(p.read_text() + '{code}' if p.exists() else '{code}'); "
            f"sys.exit({exit_code})"
        )
        return runner.Suite(code, code, (sys.executable, "-c", program), 30)

    results, exit_code = runner.run_suites(
        [suite("SC", 1), suite("SR", 0), suite("VI", 0), suite("VQ", 0)],
        cwd=tmp_path,
    )

    assert marker.read_text() == "SCSR VIVQ".replace(" ", "")
    assert [result.status for result in results] == ["NG", "OK", "OK", "OK"]
    assert exit_code == 1


def test_run_suites_returns_two_for_runner_or_environment_error(tmp_path):
    """An exit code other than 0/1 is infrastructure ERROR and dominates NG."""
    runner = load_runner()

    def suite(code: str, exit_code: int):
        return runner.Suite(
            code,
            code,
            (sys.executable, "-c", f"raise SystemExit({exit_code})"),
            30,
        )

    results, exit_code = runner.run_suites(
        [suite("SC", 1), suite("SR", 2), suite("VI", 0), suite("VQ", 0)],
        cwd=tmp_path,
    )

    assert [result.status for result in results] == ["NG", "ERROR", "OK", "OK"]
    assert exit_code == 2


def test_windows_batch_launcher_invokes_python_without_cmd_parse_errors(tmp_path):
    """The double-click launcher must be parseable by the real Windows cmd.exe."""
    batch = tmp_path / "run_all_autotests.bat"
    shutil.copy2(PROJECT_ROOT / "run_all_autotests.bat", batch)
    (tmp_path / "run_all_autotests.py").write_text(
        "print('RUNNER_STUB_OK')\n", encoding="utf-8"
    )
    env = dict(
        os.environ,
        VIMO_TEST_PYTHON=sys.executable,
        VIMO_TEST_NO_PAUSE="1",
    )

    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", str(batch)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, output
    assert "RUNNER_STUB_OK" in output
    assert "not recognized as an internal or external command" not in output

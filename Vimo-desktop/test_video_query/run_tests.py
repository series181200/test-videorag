"""Run pytest and Vitest separately; retain raw evidence and aggregate by VQ ID."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
EXPECTED = {"pytest": {"TC-VQ-001": 1, "TC-VQ-002": 1},
            "vitest": {"TC-VQ-003": 1, "TC-VQ-004": 1}}


def run(command, *, cwd=ROOT, timeout=120):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", NO_COLOR="1")
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return result.returncode, result.stdout + result.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, str(error)


def git(*args):
    code, output = run(["git", "-c", f"safe.directory={REPO.as_posix()}", *args], cwd=REPO, timeout=15)
    return output.strip() if code == 0 else None


def identify(name):
    match = re.search(r"TC[-_]VQ[-_]00[1-4]", name)
    return match.group().replace("_", "-") if match else "UNMAPPED"


def parse_pytest(file):
    rows = []
    for case in ET.parse(file).getroot().iter("testcase"):
        problem = next((case.find(tag) for tag in ("error", "failure", "skipped") if case.find(tag) is not None), None)
        name = case.get("name", "")
        status = "passed" if problem is None else {"failure": "failed", "error": "error", "skipped": "skipped"}[problem.tag]
        rows.append({"framework": "pytest", "id": identify(name), "name": name,
                     "status": status, "detail": "" if problem is None else (problem.text or problem.get("message", ""))})
    return rows


def parse_vitest(file):
    report = json.loads(file.read_text(encoding="utf-8"))
    rows = []
    for suite in report.get("testResults", []):
        for case in suite.get("assertionResults", []):
            name = case.get("fullName") or case["title"]
            rows.append({"framework": "vitest", "id": identify(name), "name": name,
                         "status": case["status"], "detail": "\n".join(case.get("failureMessages", []))})
    return rows, bool(report.get("numRuntimeErrorTestSuites") or report.get("unhandledErrors"))


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    output = ROOT / "results" / f"{stamp}-{os.getpid()}"
    output.mkdir(parents=True)
    sources = [ROOT.parent / "python_backend/videorag_api.py",
               ROOT.parent / "src/renderer/src/hooks/useChat.ts",
               ROOT.parent / "src/renderer/src/utils/chat.ts"]
    inputs = sources + sorted(p for p in ROOT.iterdir() if p.suffix in (".py", ".ts", ".tsx", ".ini", ".json", ".txt"))
    manifest = {"startedAt": stamp, "python": sys.version, "pythonExecutable": sys.executable,
                "commit": git("rev-parse", "HEAD"), "workingTree": git("status", "--short"),
                "files": [{"path": p.relative_to(REPO).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]}
    _, manifest["pytestVersion"] = run([sys.executable, "-m", "pytest", "--version"])
    checks, errors = [], []
    commands = {}
    commands["pytest"] = [sys.executable, "-m", "pytest", "-c", str(ROOT / "pytest.ini"), str(ROOT),
                           "-q", f"--junitxml={output / 'pytest.xml'}", f"--basetemp={output / 'pytest-temp'}"]
    # Keep execution sequential and continue to Vitest even when backend assertions fail.
    code, log = run(commands["pytest"])
    (output / "pytest-console.txt").write_text(log, encoding="utf-8")
    try:
        checks.extend(parse_pytest(output / "pytest.xml"))
    except (OSError, ET.ParseError) as error:
        errors.append(f"pytest report unavailable: {error}")
    if code not in (0, 1):
        errors.append(f"pytest exited with {code}")

    probe = "process.stdout.write(require.resolve('vitest/package.json',{paths:[process.argv[1],process.argv[2]]}))"
    resolved, package = run(["node", "-e", probe, str(ROOT), str(ROOT.parent / "test_renderer")])
    if resolved:
        errors.append("Vitest unavailable; install test_video_query/package.json dependencies")
        (output / "vitest-console.txt").write_text(package, encoding="utf-8")
    else:
        try:
            package_path = Path(package.strip())
            version = json.loads(package_path.read_text(encoding="utf-8"))["version"]
            manifest["vitestVersion"], manifest["vitestPackage"] = version, str(package_path)
            if version != "2.1.9":
                raise ValueError(f"Expected Vitest 2.1.9, got {version}")
            _, manifest["nodeVersion"] = run(["node", "--version"])
            commands["vitest"] = ["node", str(package_path.parent / "vitest.mjs"), "run", "--config", str(ROOT / "vitest.config.ts"),
                                    "--reporter=verbose", "--reporter=json", f"--outputFile.json={output / 'vitest.json'}"]
            code, log = run(commands["vitest"])
            (output / "vitest-console.txt").write_text(log, encoding="utf-8")
            rows, runtime_errors = parse_vitest(output / "vitest.json")
            checks.extend(rows)
            if code not in (0, 1) or runtime_errors or (code != 0 and rows and all(row["status"] == "passed" for row in rows)):
                errors.append(f"Vitest execution error (exit {code})")
        except (OSError, ValueError, KeyError) as error:
            errors.append(str(error))
    manifest["commands"] = commands
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for framework, counts in EXPECTED.items():
        for case_id, count in counts.items():
            actual = sum(c["framework"] == framework and c["id"] == case_id for c in checks)
            if actual != count:
                errors.append(f"{framework} {case_id}: expected {count}, collected {actual}")
    if any(c["id"] == "UNMAPPED" or c["status"] == "error" for c in checks):
        errors.append("Unmapped test or fixture/collection error")
    for check in checks:
        check["blockedBeforeWorker"] = check["status"] != "passed" and "BLOCKED_BEFORE_WORKER" in check["detail"]
    groups = []
    for case_id in sorted({case_id for counts in EXPECTED.values() for case_id in counts}):
        cases = [c for c in checks if c["id"] == case_id]
        count = sum(expected.get(case_id, 0) for expected in EXPECTED.values())
        passed = sum(c["status"] == "passed" for c in cases)
        status = "ERROR" if len(cases) != count or any(c["status"] == "error" for c in cases) else "PASS" if passed == count else "FAIL"
        groups.append({"id": case_id, "status": status, "expected": count, "passed": passed,
                       "failed": sum(c["status"] == "failed" for c in cases),
                       "blockedBeforeWorker": sum(c["blockedBeforeWorker"] for c in cases)})
    exit_code = 2 if errors else 0 if all(group["status"] == "PASS" for group in groups) else 1
    summary = {"exitCode": exit_code, "infrastructureErrors": errors, "groups": groups, "checks": checks}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(groups[0]))
        writer.writeheader()
        writer.writerows(groups)
    suites = ET.Element("testsuites")
    for framework in EXPECTED:
        rows = [c for c in checks if c["framework"] == framework]
        suite = ET.SubElement(suites, "testsuite", name=framework, tests=str(len(rows)),
                              failures=str(sum(c["status"] == "failed" for c in rows)),
                              errors=str(sum(c["status"] == "error" for c in rows)))
        for check in rows:
            case = ET.SubElement(suite, "testcase", classname=check["id"], name=check["name"])
            if check["status"] != "passed":
                tag = {"failed": "failure", "error": "error"}.get(check["status"], "skipped")
                ET.SubElement(case, tag).text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", check["detail"])
    if errors:
        suite = ET.SubElement(suites, "testsuite", name="runner", tests="1", errors="1")
        ET.SubElement(ET.SubElement(suite, "testcase", name="infrastructure"), "error").text = "\n".join(errors)
    ET.ElementTree(suites).write(output / "combined.xml", encoding="utf-8", xml_declaration=True)
    for group in groups:
        print(f"{group['id']} {group['status']} ({group['passed']}/{group['expected']} checks passed; {group['blockedBeforeWorker']} blocked before worker)")
    print(f"Reports: {output}")
    for error in errors:
        print(error, file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

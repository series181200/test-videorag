"""Run the four Vimo test layers and print one normalized result per test case."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def configure_console() -> None:
    """Keep Chinese case names readable in Windows terminals and redirected logs."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class CaseMeta:
    key: str
    interface: str
    failure_finding: str


@dataclass
class CaseResult:
    layer: str
    interface: str
    status: str
    finding: str
    detail: str = ""


RENDERER_CASES = [
    CaseMeta(
        "01 初始化向导可以完成首次配置",
        "InitializationWizard / loadSettings、selectFolder、saveSettings",
        "首次配置流程无法完成，用户不能进入应用主页。",
    ),
    CaseMeta(
        "02 上传视频并拦截重复上传",
        "useVideoUpload / selectVideoFiles 与重复文件校验",
        "视频选择或重复上传拦截失效，可能重复分析同一视频。",
    ),
    CaseMeta(
        "03 开始分析后进入完成状态",
        "视频分析流程 / uploadVideo、getStatus",
        "视频分析状态无法从处理中进入完成状态。",
    ),
    CaseMeta(
        "04 分析完成后可以发送问题并收到回答",
        "ChatInput 与查询流程 / queryVideo、getStatus",
        "完成分析后无法发送问题或显示模型回答。",
    ),
    CaseMeta(
        "05 分析失败后显示错误反馈",
        "分析异常反馈 / getStatus(error)",
        "分析失败时页面没有向用户显示明确错误反馈。",
    ),
]


COMMUNICATION_CASES = [
    CaseMeta(
        "exposes the Electron and application APIs",
        "preload / contextBridge.exposeInMainWorld",
        "preload 未正确暴露 Electron 或应用 API，renderer 无法通信。",
    ),
    CaseMeta(
        "provides the generic invoke function declared and used by renderer",
        "preload / window.api.invoke",
        "renderer 使用的 window.api.invoke 未被 preload 暴露，运行时会出现 not a function。",
    ),
    CaseMeta(
        "returns metadata for every selected video",
        "file-handlers / select-video-files",
        "Windows 视频路径未正确提取文件名，界面可能显示完整本地路径。",
    ),
    CaseMeta(
        "returns complete defaults when configuration files are absent",
        "settings / load-settings",
        "首次启动缺少配置文件时，默认设置加载不完整。",
    ),
    CaseMeta(
        "writes session data with a last-updated timestamp",
        "chat-session-handlers / save-chat-session",
        "聊天会话或更新时间未正确持久化。",
    ),
    CaseMeta(
        "maps health checks to the Python health endpoint",
        "videorag-handlers / videorag:health-check",
        "健康检查没有正确映射到 Python API。",
    ),
    CaseMeta(
        "maps video uploads to the expected backend payload",
        "videorag-handlers / videorag:upload-video",
        "视频上传的 URL、请求方法或请求体映射错误。",
    ),
    CaseMeta(
        "returns backend error text as a serializable IPC failure",
        "videorag-handlers / callVideoRAGAPI 错误转换",
        "Python 后端错误没有转换成 renderer 可处理的结构化响应。",
    ),
]


API_CASES = [
    CaseMeta("test_health_endpoint_is_available", "create_app / GET /api/health", "健康接口不可用或响应契约错误。"),
    CaseMeta("test_initialize_rejects_empty_json_body", "POST /api/initialize", "初始化接口接受空 JSON，可能产生无效全局配置。"),
    CaseMeta("test_imagebind_status_keeps_status_contract", "GET /api/imagebind/status", "ImageBind 状态接口缺少约定字段。"),
    CaseMeta("test_non_string_query_is_rejected", "POST /api/sessions/<chat_id>/query", "查询接口接受非字符串内容，可能触发后续处理异常。"),
    CaseMeta("test_index_worker_enters_error_when_imagebind_unavailable", "index_video_worker_process", "ImageBind 不可用时索引任务没有进入错误状态。"),
    CaseMeta("test_index_worker_enters_error_when_videorag_fails", "index_video_worker_process", "VideoRAG 索引异常没有被记录为错误状态。"),
    CaseMeta("test_query_worker_enters_error_when_query_fails", "query_worker_process", "查询异常没有被记录，前端可能一直等待。"),
    CaseMeta("test_video_indexing_starts_and_is_recorded", "VideoRAGProcessManager.start_video_indexing", "索引子进程没有启动或没有登记运行状态。"),
    CaseMeta("test_terminate_session_stops_related_processes", "VideoRAGProcessManager.terminate_process", "终止会话后仍残留索引或查询进程。"),
    CaseMeta("test_missing_query_does_not_start_process", "POST /api/sessions/<chat_id>/query", "缺少 query 字段时仍启动后台进程。"),
    CaseMeta("test_global_config_does_not_log_api_keys", "VideoRAGProcessManager.set_global_config", "日志中泄露 OpenAI 或 DashScope API Key。"),
    CaseMeta("test_status_json_write_and_read", "write_status_json / read_status_json", "状态 JSON 无法可靠写入或读回。"),
    CaseMeta("test_session_status_merges_index_and_query", "update_session_status", "索引状态和查询状态相互覆盖或合并失败。"),
    CaseMeta("test_concurrent_status_updates_are_safe", "update_session_status 并发写入", "并发状态更新发生异常或造成状态文件竞争。"),
]


ALGORITHM_CASES = [
    CaseMeta("test_query_param_defaults_match_default_query_strategy", "QueryParam 默认构造", "默认查询策略或参数值错误。"),
    CaseMeta("test_locate_json_inside_model_response", "locate_json_string_body_from_string", "无法从模型包装文本中提取合法 JSON。"),
    CaseMeta("test_truncate_list_uses_inclusive_token_boundary", "truncate_list_by_token_size", "恰好达到 Token 上限的数据被错误丢弃或超限数据未截断。"),
    CaseMeta("test_token_size_chunking_obeys_size_and_overlap", "chunking_by_token_size", "Token 分块大小、重叠内容或元数据错误。"),
    CaseMeta("test_video_segments_are_grouped_without_crossing_limit", "chunking_by_video_segments", "视频段合并后超过 Token 上限或 segment ID 丢失。"),
    CaseMeta("test_index_done_callback_persists_and_reloads_json", "JsonKVStorage.index_done_callback", "索引完成后数据未持久化或重新加载内容不一致。"),
    CaseMeta(
        "test_async_limit_releases_capacity_after_exception",
        "limit_async_func_call",
        "模型调用异常后并发容量没有释放，后续分析或查询可能永久等待。",
    ),
]


def command_path(*relative_parts: str, fallback: str) -> str | None:
    candidate = ROOT.joinpath(*relative_parts)
    if candidate.exists():
        return str(candidate)
    return shutil.which(fallback)


def run_command(command: list[str], *, env: dict[str, str] | None = None, timeout: int = 180):
    merged_env = os.environ.copy()
    merged_env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    if env:
        merged_env.update(env)
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return completed.returncode, completed.stdout
    except FileNotFoundError as error:
        return 127, str(error)
    except subprocess.TimeoutExpired as error:
        output = error.stdout if isinstance(error.stdout, str) else ""
        return 124, f"{output}\n测试命令超过 {timeout} 秒未结束"


def short_error(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1][:240] if lines else "没有生成可读取的测试结果"


def normalized_results(
    layer: str,
    metadata: list[CaseMeta],
    observed: dict[str, tuple[str, str]],
    layer_error: str = "",
) -> list[CaseResult]:
    results: list[CaseResult] = []
    known_keys = {case.key for case in metadata}
    for case in metadata:
        if case.key in observed:
            status, detail = observed[case.key]
            finding = "未发现漏洞" if status == "OK" else case.failure_finding
        else:
            status = "NG"
            detail = layer_error or "测试框架未返回该用例的结果"
            finding = f"测试环境问题，未完成执行（非业务漏洞）：{detail}"
        results.append(CaseResult(layer, case.interface, status, finding, detail))

    for key, (status, detail) in observed.items():
        if key not in known_keys:
            finding = "未发现漏洞" if status == "OK" else f"未登记的新失败：{detail}"
            results.append(CaseResult(layer, key, status, finding, detail))
    return results


def run_renderer(temp_dir: Path) -> list[CaseResult]:
    layer = "前端页面层"
    vitest = command_path(
        "test_renderer",
        "node_modules",
        ".bin",
        "vitest.cmd" if os.name == "nt" else "vitest",
        fallback="vitest",
    )
    if not vitest:
        return normalized_results(
            layer,
            RENDERER_CASES,
            {},
            "缺少 Vitest，请先执行 npm.cmd install --prefix test_renderer",
        )

    result_file = temp_dir / "renderer.json"
    code, output = run_command(
        [
            vitest,
            "run",
            "--config",
            "test_renderer/vitest.config.ts",
            "--reporter=json",
            f"--outputFile={result_file}",
        ],
        timeout=120,
    )
    if not result_file.exists():
        return normalized_results(layer, RENDERER_CASES, {}, f"Vitest 未生成结果：{short_error(output)}")

    report = json.loads(result_file.read_text(encoding="utf-8"))
    observed: dict[str, tuple[str, str]] = {}
    for suite in report.get("testResults", []):
        for assertion in suite.get("assertionResults", []):
            status = "OK" if assertion.get("status") == "passed" else "NG"
            detail = "\n".join(assertion.get("failureMessages", []))
            observed[assertion.get("title", "unknown renderer test")] = (status, detail)
    return normalized_results(layer, RENDERER_CASES, observed, short_error(output) if code else "")


def run_communication(temp_dir: Path) -> list[CaseResult]:
    layer = "前后端通信层"
    vitest = command_path(
        "test_communication",
        "node_modules",
        ".bin",
        "vitest.cmd" if os.name == "nt" else "vitest",
        fallback="vitest",
    )
    if not vitest:
        return normalized_results(
            layer,
            COMMUNICATION_CASES,
            {},
            "缺少 Vitest，请先执行 npm.cmd install --prefix test_communication",
        )

    result_file = temp_dir / "communication.json"
    code, output = run_command(
        [
            vitest,
            "run",
            "--config",
            "test_communication/filtered/vitest.config.ts",
            "--reporter=json",
            f"--outputFile={result_file}",
        ],
        timeout=90,
    )
    if not result_file.exists():
        return normalized_results(layer, COMMUNICATION_CASES, {}, f"Vitest 未生成结果：{short_error(output)}")

    report = json.loads(result_file.read_text(encoding="utf-8"))
    observed: dict[str, tuple[str, str]] = {}
    for suite in report.get("testResults", []):
        for assertion in suite.get("assertionResults", []):
            status = "OK" if assertion.get("status") == "passed" else "NG"
            detail = "\n".join(assertion.get("failureMessages", []))
            observed[assertion.get("title", "unknown communication test")] = (status, detail)
    return normalized_results(layer, COMMUNICATION_CASES, observed, short_error(output) if code else "")


def run_api(temp_dir: Path) -> list[CaseResult]:
    layer = "后端与算法通信层"
    result_file = temp_dir / "api.xml"
    base_temp = temp_dir / "api-pytest-temp"
    code, output = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            "test_videorag_api/pytest.ini",
            "test_videorag_api/tests",
            f"--junitxml={result_file}",
            f"--basetemp={base_temp}",
            "-q",
        ],
        env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        timeout=120,
    )
    if not result_file.exists():
        return normalized_results(layer, API_CASES, {}, f"pytest 未生成结果：{short_error(output)}")

    observed: dict[str, tuple[str, str]] = {}
    for test_case in ET.parse(result_file).getroot().iter("testcase"):
        failure = test_case.find("failure")
        error = test_case.find("error")
        skipped = test_case.find("skipped")
        problem = next(
            (node for node in (failure, error, skipped) if node is not None),
            None,
        )
        status = "OK" if problem is None else "NG"
        detail = "" if problem is None else (problem.get("message") or problem.text or "")
        observed[test_case.get("name", "unknown API test")] = (status, detail)
    return normalized_results(layer, API_CASES, observed, short_error(output) if code else "")


def run_algorithm(temp_dir: Path) -> list[CaseResult]:
    layer = "VideoRAG 算法层"
    result_file = temp_dir / "algorithm.xml"
    base_temp = temp_dir / "pytest-temp"
    code, output = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            "test_videorag_algorithm/filtered/pytest.ini",
            "test_videorag_algorithm/filtered",
            f"--junitxml={result_file}",
            f"--basetemp={base_temp}",
            "-q",
        ],
        env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        timeout=90,
    )
    if not result_file.exists():
        return normalized_results(layer, ALGORITHM_CASES, {}, f"pytest 未生成结果：{short_error(output)}")

    observed: dict[str, tuple[str, str]] = {}
    for test_case in ET.parse(result_file).getroot().iter("testcase"):
        failure = test_case.find("failure")
        error = test_case.find("error")
        skipped = test_case.find("skipped")
        problem = next(
            (node for node in (failure, error, skipped) if node is not None),
            None,
        )
        status = "OK" if problem is None else "NG"
        detail = "" if problem is None else (problem.get("message") or problem.text or "")
        observed[test_case.get("name", "unknown algorithm test")] = (status, detail)
    return normalized_results(layer, ALGORITHM_CASES, observed, short_error(output) if code else "")


def print_results(results: list[CaseResult]) -> None:
    print("\n" + "=" * 96)
    print("Vimo 四层统一测试结果")
    print("=" * 96)
    current_layer = ""
    for index, result in enumerate(results, start=1):
        if result.layer != current_layer:
            current_layer = result.layer
            print(f"\n【{current_layer}】")
        print(
            f"{index:02d}. [{result.status}] "
            f"测试层级：{result.layer} | "
            f"测试接口/函数：{result.interface} | "
            f"发现漏洞：{result.finding}"
        )

    print("\n" + "-" * 96)
    print("分层汇总")
    print("-" * 96)
    layers: list[str] = []
    for result in results:
        if result.layer not in layers:
            layers.append(result.layer)
    for layer in layers:
        layer_results = [result for result in results if result.layer == layer]
        ok_count = sum(result.status == "OK" for result in layer_results)
        ng_count = len(layer_results) - ok_count
        print(f"{layer}：总数 {len(layer_results)}，OK {ok_count}，NG {ng_count}")
    ok_count = sum(result.status == "OK" for result in results)
    ng_count = len(results) - ok_count
    print(f"总计：{len(results)} 条，OK {ok_count}，NG {ng_count}")
    print("=" * 96)


def main() -> int:
    configure_console()
    all_results: list[CaseResult] = []
    with tempfile.TemporaryDirectory(prefix=".unified-test-", dir=ROOT) as temp_name:
        temp_dir = Path(temp_name)
        runners = [
            ("前端页面层", run_renderer),
            ("前后端通信层（filtered）", run_communication),
            ("后端与算法通信层", run_api),
            ("VideoRAG 算法层（filtered）", run_algorithm),
        ]
        for label, runner in runners:
            print(f"[启动] {label}...", flush=True)
            try:
                all_results.extend(runner(temp_dir))
            except Exception as error:  # Keep later layers running after a runner defect.
                metadata = {
                    "前端页面层": RENDERER_CASES,
                    "前后端通信层（filtered）": COMMUNICATION_CASES,
                    "后端与算法通信层": API_CASES,
                    "VideoRAG 算法层（filtered）": ALGORITHM_CASES,
                }[label]
                all_results.extend(
                    normalized_results(label, metadata, {}, f"统一运行器异常：{error}")
                )

    print_results(all_results)
    return 0 if all(result.status == "OK" for result in all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

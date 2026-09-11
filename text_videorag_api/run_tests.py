"""运行按功能分类的 18 项 VideoRAG API 测试。"""

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TEST_NAMES = {
    "test_health_endpoint_is_available": "健康接口可用",
    "test_imagebind_status_keeps_status_contract": "ImageBind 状态字段契约",
    "test_initialize_rejects_empty_json_body": "初始化接口拒绝空 JSON",
    "test_missing_query_does_not_start_process": "缺少查询内容时拒绝启动任务",
    "test_non_string_query_is_rejected": "拒绝非字符串查询",
    "test_imagebind_load_requires_initialization": "模型加载前必须完成初始化",
    "test_index_worker_enters_error_when_imagebind_unavailable": "ImageBind 不可用时索引进入错误状态",
    "test_index_worker_enters_error_when_videorag_fails": "VideoRAG 失败时索引进入错误状态",
    "test_query_worker_enters_error_when_query_fails": "查询失败时进入错误状态",
    "test_duplicate_indexing_is_not_started_twice": "同一会话不重复启动索引",
    "test_terminate_session_stops_related_processes": "终止会话时停止关联进程",
    "test_video_indexing_starts_and_is_recorded": "索引任务启动并记录",
    "test_delete_session_removes_status_directory": "删除会话后清理状态目录",
    "test_empty_query_does_not_start_process": "空查询不启动任务",
    "test_system_status_excludes_finished_processes": "系统状态排除已结束进程",
    "test_global_config_does_not_log_api_keys": "配置日志不泄露 API Key",
    "test_chat_id_cannot_escape_storage_directory": "会话 ID 不得越出存储目录",
    "test_concurrent_status_updates_are_safe": "并发状态更新安全",
    "test_corrupted_status_json_returns_empty_data": "损坏 JSON 安全降级",
    "test_session_status_merges_index_and_query": "索引和查询状态正确合并",
    "test_status_json_write_and_read": "状态文件正常读写",
}


def display_name(test: unittest.TestCase) -> str:
    """Return a stable Chinese name while retaining the Python test identity."""
    method_name = test.id().split(".")[-1]
    return TEST_NAMES.get(method_name, method_name)


class ReadableResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        print(f"[执行] {display_name(test)}")

    def addSuccess(self, test):
        super().addSuccess(test)
        print(f"[通过] {display_name(test)}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(f"[失败] {display_name(test)} - 发现业务缺陷")

    def addError(self, test, err):
        super().addError(test, err)
        print(f"[错误] {display_name(test)} - 测试执行异常")


def run() -> unittest.TestResult:
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT)
    )
    started_at = time.perf_counter()
    result = unittest.TextTestRunner(
        stream=sys.stdout, verbosity=0, resultclass=ReadableResult
    ).run(suite)
    elapsed = time.perf_counter() - started_at
    total = result.testsRun
    failed = len(result.failures)
    errors = len(result.errors)
    passed = total - failed - errors

    print("\n" + "=" * 72)
    print("VideoRAG API 按功能分类测试报告")
    print("=" * 72)
    print(f"测试总数 : {total}/18")
    print(f"通过数量 : {passed}")
    print(f"失败数量 : {failed}（发现的业务缺陷）")
    print(f"错误数量 : {errors}（测试环境或测试代码异常）")
    print(f"通过率   : {passed / total * 100:.1f}%" if total else "通过率   : 0.0%")
    print(f"耗时     : {elapsed:.2f} 秒")
    if errors:
        print("结论     : 存在测试执行异常，请先检查环境或测试代码。")
    elif failed:
        print("结论     : 已复现业务缺陷，可用于问题展示和测试报告。")
    else:
        print("结论     : 18 项测试全部通过。")
    print("=" * 72)
    return result


if __name__ == "__main__":
    sys.exit(0 if run().wasSuccessful() else 1)

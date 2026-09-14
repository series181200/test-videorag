"""运行按五类测试方法分类的 VideoRAG API 测试。"""

from collections import defaultdict
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
    "test_concurrent_status_updates_are_safe": "并发状态更新安全",
    "test_session_status_merges_index_and_query": "索引和查询状态正确合并",
    "test_status_json_write_and_read": "状态文件正常读写",
}

TEST_METHODS = {
    "test_health_endpoint_is_available": "契约测试法",
    "test_initialize_rejects_empty_json_body": "契约测试法",
    "test_imagebind_status_keeps_status_contract": "契约测试法",
    "test_non_string_query_is_rejected": "契约测试法",
    "test_empty_query_does_not_start_process": "契约测试法",
    "test_missing_query_does_not_start_process": "契约测试法",
    "test_global_config_does_not_log_api_keys": "契约测试法",
    "test_status_json_write_and_read": "契约测试法",
    "test_index_worker_enters_error_when_imagebind_unavailable": "异常注入法",
    "test_index_worker_enters_error_when_videorag_fails": "异常注入法",
    "test_query_worker_enters_error_when_query_fails": "异常注入法",
    "test_video_indexing_starts_and_is_recorded": "状态迁移测试法",
    "test_terminate_session_stops_related_processes": "状态迁移测试法",
    "test_delete_session_removes_status_directory": "状态迁移测试法",
    "test_system_status_excludes_finished_processes": "状态迁移测试法",
    "test_session_status_merges_index_and_query": "状态迁移测试法",
    "test_duplicate_indexing_is_not_started_twice": "幂等性测试法",
    "test_concurrent_status_updates_are_safe": "并发测试法",
}


def display_name(test: unittest.TestCase) -> str:
    """Return a stable Chinese name while retaining the Python test identity."""
    name = test.id().split(".")[-1]
    return TEST_NAMES.get(name, name)


def test_method(test: unittest.TestCase) -> str:
    """Return the five-method classification for a test."""
    name = test.id().split(".")[-1]
    return TEST_METHODS.get(name, "未归类")


class ReadableResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream=stream, descriptions=descriptions, verbosity=verbosity)
        self.method_stats = defaultdict(lambda: {"total": 0, "failed": 0, "errors": 0})

    def startTest(self, test):
        super().startTest(test)
        self.method_stats[test_method(test)]["total"] += 1
        print(f"[执行] {display_name(test)}")

    def addSuccess(self, test):
        super().addSuccess(test)
        print(f"[通过] {display_name(test)}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.method_stats[test_method(test)]["failed"] += 1
        print(f"[失败] {display_name(test)} - 发现业务缺陷")

    def addError(self, test, err):
        super().addError(test, err)
        self.method_stats[test_method(test)]["errors"] += 1
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
    print("VideoRAG API 按测试方法分类测试报告")
    print("=" * 72)
    print(f"测试总数 : {total}")
    print(f"通过数量 : {passed}")
    print(f"失败数量 : {failed}（发现的业务缺陷）")
    print(f"错误数量 : {errors}（测试环境或测试代码异常）")
    print(f"通过率   : {passed / total * 100:.1f}%" if total else "通过率   : 0.0%")
    print(f"耗时     : {elapsed:.2f} 秒")
    print("测试方法统计:")
    for name, stats in result.method_stats.items():
        method_failed = stats["failed"] + stats["errors"]
        passed_count = stats["total"] - method_failed
        print(f"  {name}: 共 {stats['total']} 条，通过 {passed_count} 条，失败 {method_failed} 条")
    if errors:
        print("结论     : 存在测试执行异常，请先检查环境或测试代码。")
    elif failed:
        print("结论     : 已复现业务缺陷，可用于问题展示和测试报告。")
    else:
        print(f"结论     : {total} 项测试全部通过。")
    print("=" * 72)
    return result


if __name__ == "__main__":
    sys.exit(0 if run().wasSuccessful() else 1)

from python_support import require_started


def test_TC_VQ_003_timeout_clears_active_answer_and_allows_retry(runtime, model):
    runtime.prepare(old_answer="old answer")
    model.side_effect = TimeoutError("model timed out")
    process = require_started(runtime.query("failing question"), runtime)
    assert runtime.status()["query_status"].get("answer") is None
    process.run()  # Runs the real worker with a model boundary that raises TimeoutError.
    assert model.call_count == 1, "The test must actually reach the model boundary"
    failed = runtime.status()["query_status"]
    assert failed["status"] == "error"
    assert "timed out" in failed["message"]
    assert failed.get("answer") is None
    assert not process.is_alive()
    status = runtime.manager.get_process_status()
    assert "vq-session_query" not in status or not status["vq-session_query"]["is_alive"]
    model.side_effect = None
    retry = require_started(runtime.query("retry question"), runtime)
    retry.run()
    final = runtime.status()["query_status"]
    assert final["status"] == "completed"
    assert final["query"] == "retry question"
    assert final["answer"] == "new answer"
    assert model.call_count == 2
    assert not retry.is_alive()

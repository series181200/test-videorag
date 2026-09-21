from python_support import require_started


def test_TC_VQ_004_busy_session_rejects_B_preserves_A_then_accepts_B(runtime, model):
    runtime.prepare()
    model.side_effect = lambda query, param: "answer to " + query
    first = require_started(runtime.query("question A"), runtime)
    before = runtime.status()
    rejected = runtime.query("question B")
    assert rejected.status_code == 409, rejected.get_json()
    assert rejected.get_json()["success"] is False
    assert len(runtime.processes) == 1
    assert runtime.manager.running_processes["vq-session_query"]["process"] is first
    assert runtime.status() == before
    first.run()
    assert runtime.status()["query_status"]["answer"] == "answer to question A"
    second = require_started(runtime.query("question B"), runtime)
    assert second is not first
    second.run()
    assert runtime.status()["query_status"]["query"] == "question B"
    assert runtime.status()["query_status"]["answer"] == "answer to question B"
    assert [call.kwargs["query"] for call in model.call_args_list] == ["question A", "question B"]

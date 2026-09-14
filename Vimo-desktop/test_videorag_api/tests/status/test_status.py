"""Status file and concurrent persistence tests implemented with pytest."""

import threading

from tests.support import api_module

api = api_module()


def test_status_json_write_and_read(tmp_path):
    path = str(tmp_path / "status.json")
    expected = {"indexing_status": {"status": "processing"}}

    api.write_status_json(path, expected)

    assert api.read_status_json(path) == expected


def test_session_status_merges_index_and_query(tmp_path):
    base_path = str(tmp_path)
    api.update_session_status(
        "status-chat", base_path, "indexing_status", {"status": "ok"}
    )
    api.update_session_status(
        "status-chat", base_path, "query_status", {"query": "hello"}
    )
    path = api.get_session_status_file("status-chat", base_path)

    status = api.read_status_json(path)

    assert status["indexing_status"]["status"] == "ok"
    assert status["query_status"]["query"] == "hello"


def test_concurrent_status_updates_are_safe(tmp_path):
    errors = []
    barrier = threading.Barrier(2)

    def update(status_type):
        try:
            barrier.wait()
            api.update_session_status(
                "concurrent",
                str(tmp_path),
                status_type,
                {"status": "processing"},
            )
        except Exception as error:  # The assertion below exposes any thread failure.
            errors.append(error)

    threads = [
        threading.Thread(target=update, args=("indexing_status",)),
        threading.Thread(target=update, args=("query_status",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, errors

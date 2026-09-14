"""Security regression tests implemented with pytest."""

from unittest.mock import MagicMock

from tests.support import api_module

api = api_module()


def test_global_config_does_not_log_api_keys(monkeypatch):
    manager = api.VideoRAGProcessManager()
    log = MagicMock()
    monkeypatch.setattr(api, "log_to_file", log)

    manager.set_global_config(
        {
            "openai_api_key": "openai-secret",
            "ali_dashscope_api_key": "dashscope-secret",
        }
    )

    logged_text = " ".join(str(call) for call in log.call_args_list)
    assert "openai-secret" not in logged_text
    assert "dashscope-secret" not in logged_text

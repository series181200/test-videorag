"""Security regression tests."""

import unittest
from unittest.mock import patch

from tests.support import api_module

api = api_module()


class TestSecurity(unittest.TestCase):
    def test_global_config_does_not_log_api_keys(self):
        manager = api.VideoRAGProcessManager()
        with patch.object(api, "log_to_file") as log:
            manager.set_global_config({
                "openai_api_key": "openai-secret",
                "ali_dashscope_api_key": "dashscope-secret",
            })
        logged_text = " ".join(str(call) for call in log.call_args_list)
        self.assertNotIn("openai-secret", logged_text)
        self.assertNotIn("dashscope-secret", logged_text)

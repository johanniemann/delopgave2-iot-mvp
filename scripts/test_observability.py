"""The failure demonstration must stay local and restore its own database."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import observability as demo


class ObservabilitySafetyTests(unittest.TestCase):
    def test_inherited_variables_cannot_redirect_the_demo(self):
        with patch.dict(os.environ, {"APP_PORT": "443", "APP_MODE": "shared",
                                     "COMPOSE_PROJECT_NAME": "aeris-shared"}), patch.object(demo, "run") as run:
            demo.compose("app", "stop", "db")
        args = run.call_args.args[0]
        self.assertIn("aeris-observed", args)
        self.assertNotIn("aeris-shared", args)
        environment = run.call_args.kwargs["env"]
        self.assertEqual(environment["APP_PORT"], "8766")
        self.assertEqual(environment["APP_MODE"], "local")
        self.assertNotIn("COMPOSE_PROJECT_NAME", environment)

    def test_failure_test_refuses_a_different_published_address(self):
        with patch.object(demo, "compose", return_value=subprocess.CompletedProcess([], 0, "0.0.0.0:8765\n")), \
                patch.object(demo, "get") as get:
            with self.assertRaisesRegex(SystemExit, "Refusing"):
                demo.failure_demo()
            get.assert_not_called()

    def test_database_is_restarted_even_when_a_test_request_fails(self):
        responses = [(200, json.dumps({"cases": [{"id": "QA-CASE"}]}).encode()),
                     (200, b"saved case"), URLError("interrupted")]
        with patch.object(demo, "require_local_app"), patch.object(demo, "get", side_effect=responses), \
                patch.object(demo, "compose") as compose:
            with self.assertRaises(URLError):
                demo.failure_demo()
        self.assertEqual(compose.call_args_list[0].args, ("app", "stop", "db"))
        self.assertEqual(compose.call_args_list[-1].args, ("app", "up", "-d", "--wait", "db"))

    def test_corrupt_tool_archive_never_executes_or_overwrites_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = Path(folder)
            env = runtime / ".env.observability"
            env.write_text("existing settings")
            (runtime / "foundry_darwin_arm64.tar.gz").write_bytes(b"corrupt download")
            with patch.object(demo, "RUNTIME", runtime), patch.object(demo, "ENV", env), \
                    patch.object(demo.platform, "system", return_value="Darwin"), \
                    patch.object(demo.platform, "machine", return_value="arm64"), \
                    patch.object(demo, "run") as run:
                with self.assertRaisesRegex(SystemExit, "checksum mismatch"):
                    demo.prepare()
                run.assert_not_called()
            self.assertEqual(env.read_text(), "existing settings")


if __name__ == "__main__":
    unittest.main()

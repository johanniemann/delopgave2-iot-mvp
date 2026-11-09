"""Credentials stay bound to the intended target and out of CLI arguments."""
import json
import secrets
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from api_client import ApiClient
import run_postman


class AccountHelperTests(unittest.TestCase):
    def test_plain_http_remote_and_embedded_credentials_are_rejected(self):
        for base in ("http://example.com", "https://user:secret@example.com", "https://example.com/path", "https://example.com?secret=value"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                ApiClient(base)

    def test_wrong_target_credentials_are_never_sent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'credentials.json'
            path.write_text(json.dumps({"base_url": "https://other.example", "technician": {"username": "sample", "password": secrets.token_urlsafe(24)}}))
            path.chmod(0o600)
            client = ApiClient("https://expected.example")
            with patch.object(client, 'request') as request:
                with self.assertRaisesRegex(SystemExit, 'different host'):
                    client.login(credentials_file=path)
                request.assert_not_called()

    def test_runner_uses_private_temporary_environment_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret = secrets.token_urlsafe(24)
            path = root / '.env.accounts-8765.json'
            path.write_text(json.dumps({"base_url": "http://127.0.0.1:8765", "technician": {"username": "sample", "password": secret}}))
            path.chmod(0o600)
            seen = []
            def execute(args, **kwargs):
                self.assertNotIn(secret, str(args))
                env = Path(args[-1]); seen.append(env)
                self.assertIn(secret, env.read_text())
                self.assertEqual(env.stat().st_mode & 0o777, 0o600)
                return subprocess.CompletedProcess(args, 4)
            with patch.object(run_postman, 'ROOT', root), patch('sys.argv', ['run_postman.py']), \
                    patch.object(run_postman.subprocess, 'run', side_effect=execute):
                with self.assertRaises(SystemExit) as stopped:
                    run_postman.main()
                self.assertEqual(stopped.exception.code, 4)
            self.assertFalse(seen[0].exists())
            self.assertIn(secret, path.read_text())


if __name__ == '__main__':
    unittest.main()

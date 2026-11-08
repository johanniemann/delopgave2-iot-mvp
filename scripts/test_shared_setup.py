"""Check that first-host setup cannot silently replace persisted credentials."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("setup_shared.py")


class SharedSetupTests(unittest.TestCase):
    def test_creates_private_settings_without_printing_or_overwriting_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".env.shared"
            command = [sys.executable, str(SCRIPT), "demo.example.com", "--env-file", str(target)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = target.read_bytes()
            values = dict(line.split("=", 1) for line in original.decode().splitlines())
            self.assertEqual(values["APP_MODE"], "shared")
            for name in ("POSTGRES_PASSWORD",):
                self.assertGreaterEqual(len(values[name]), 32)
                self.assertNotIn(values[name], first.stdout + first.stderr)
            if sys.platform != "win32":
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(target.read_bytes(), original)

    def test_rejects_ip_scheme_path_and_compose_interpolation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".env.shared"
            for value in ("20.91.193.131", "https://example.com", "example.com/path", "${API_TOKEN}.com", "localhost"):
                with self.subTest(value=value):
                    result = subprocess.run([sys.executable, str(SCRIPT), value, "--env-file", str(target)],
                                            capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

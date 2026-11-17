"""Local clones must not silently replace each other's Compose resources."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch

import setup_demo


class LocalSetupTests(unittest.TestCase):
    def run_setup(self, root, args=(), environment=None):
        output = io.StringIO()
        with patch.object(setup_demo, "ROOT", root), \
                patch.dict(os.environ, environment or {}, clear=True), \
                patch.object(setup_demo.socket, "socket") as socket_factory, \
                redirect_stdout(output):
            setup_demo.main(list(args))
        return output.getvalue(), socket_factory

    @staticmethod
    def settings(root):
        return dict(line.split("=", 1) for line in (root / ".env").read_text().splitlines())

    def test_two_checkouts_get_separate_persisted_projects_and_private_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "clone-one"
            second = Path(directory) / "clone-two"
            first.mkdir()
            second.mkdir()
            for root in (first, second):
                output, socket_factory = self.run_setup(root)
                values = self.settings(root)
                self.assertRegex(values["COMPOSE_PROJECT_NAME"], r"^aeris-local-[0-9a-f]{12}$")
                self.assertEqual(values["APP_MODE"], "local")
                self.assertEqual(values["APP_PORT"], "8765")
                self.assertGreaterEqual(len(values["POSTGRES_PASSWORD"]), 32)
                self.assertNotIn(values["POSTGRES_PASSWORD"], output)
                socket_factory.return_value.__enter__.return_value.bind.assert_called_once_with(("127.0.0.1", 8765))
                if os.name != "nt":
                    self.assertEqual((root / ".env").stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(self.settings(first)["COMPOSE_PROJECT_NAME"],
                                self.settings(second)["COMPOSE_PROJECT_NAME"])
            self.assertNotEqual(self.settings(first)["POSTGRES_PASSWORD"],
                                self.settings(second)["POSTGRES_PASSWORD"])

    def test_rerun_preserves_old_project_password_and_port_even_with_new_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = (f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
                        "APP_MODE=local\nAPP_PORT=8765\n").encode()
            (root / ".env").write_bytes(original)
            output, socket_factory = self.run_setup(root, ("--project", "aeris-another", "--port", "8771"))
            self.assertEqual((root / ".env").read_bytes(), original)
            self.assertIn("Existing .env preserved", output)
            socket_factory.assert_not_called()

    def test_fresh_settings_keep_explicit_ci_environment_project_and_port(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_setup(root, environment={"COMPOSE_PROJECT_NAME": "aeris-ci-isolated-123", "APP_PORT": "8771"})
            values = self.settings(root)
            self.assertEqual(values["COMPOSE_PROJECT_NAME"], "aeris-ci-isolated-123")
            self.assertEqual(values["APP_PORT"], "8771")

    def test_explicit_arguments_override_environment_for_new_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.run_setup(root, ("--project", "aeris-local-selected", "--port", "8772"),
                           {"COMPOSE_PROJECT_NAME": "aeris-environment", "APP_PORT": "8771"})
            values = self.settings(root)
            self.assertEqual(values["COMPOSE_PROJECT_NAME"], "aeris-local-selected")
            self.assertEqual(values["APP_PORT"], "8772")

    def test_occupied_port_stops_before_settings_or_credentials_are_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(setup_demo, "ROOT", root), patch.dict(os.environ, {}, clear=True), \
                    patch.object(setup_demo.socket, "socket") as socket_factory:
                socket_factory.return_value.__enter__.return_value.bind.side_effect = OSError("occupied")
                with self.assertRaisesRegex(SystemExit, "port 8771 is unavailable"):
                    setup_demo.main(["--port", "8771"])
            self.assertFalse((root / ".env").exists())

    def test_invalid_settings_and_shared_project_are_refused_before_creation(self):
        for args in (("--port", "0"), ("--port", "65536"), ("--port", "invalid"),
                     ("--project", "has a space"), ("--project", "${OTHER_PROJECT}"),
                     ("--project", "aeris-shared")):
            with self.subTest(args=args), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with redirect_stdout(io.StringIO()), patch("sys.stderr", io.StringIO()), \
                        self.assertRaises(SystemExit):
                    self.run_setup(root, args)
                self.assertFalse((root / ".env").exists())

    def test_concurrent_creator_is_preserved_instead_of_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = "POSTGRES_PASSWORD=" + secrets.token_urlsafe(32) + "\nAPP_PORT=8779\n"

            def other_creator(*args, **kwargs):
                (root / ".env").write_text(original)
                raise FileExistsError

            with patch.object(setup_demo.os, "open", side_effect=other_creator):
                output, _ = self.run_setup(root)
            self.assertEqual((root / ".env").read_text(), original)
            self.assertIn("Existing .env preserved", output)
            self.assertNotIn(original, output)


if __name__ == "__main__":
    unittest.main()

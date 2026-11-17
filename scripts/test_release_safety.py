"""Reject altered packages and prove restore failure never targets the live DB."""
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import sys
import unittest
from unittest.mock import patch

import database_backup
import promote_release


class ReleaseSafetyTests(unittest.TestCase):
    def test_relative_release_directory_updates_the_shared_pointer_after_chdir(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            maintenance = root / "maintenance"
            maintenance.mkdir()
            releases = root / "releases"
            releases.mkdir()
            old = releases / "previous"
            old.mkdir()
            current = root / "current"
            current.symlink_to(old)
            bundle = root / "incoming"
            bundle.mkdir()
            with tarfile.open(bundle / "source.tar.gz", "w:gz"):
                pass
            (bundle / "image.tar.gz").write_bytes(b"tested-image")
            revision = "a" * 40
            image_id = "sha256:" + "b" * 64
            data = {"revision": revision, "image": "ghcr.io/example/aeris:sha-" + revision,
                    "os": "linux", "architecture": "amd64", "image_id": image_id,
                    "files": {name: database_backup.digest_file(bundle / name) for name in ("image.tar.gz", "source.tar.gz")}}
            (bundle / "release.json").write_text(json.dumps(data))
            evidence = {"tables": {"scenarios": "preserved"}}
            verification = root / "backup.verified.json"
            database_backup.private_json(verification, {"verified_at": datetime.now(timezone.utc).isoformat(),
                "compose_project": "aeris-shared", "database": "aeris",
                "restored_into_isolated_database": True, "evidence": evidence})
            env_file = root / ".env.shared"
            env_file.touch(mode=0o600)
            argv = ["promote_release.py", "--bundle", "../incoming", "--revision", revision,
                    "--env-file", "../.env.shared", "--backup-verification", "../backup.verified.json",
                    "--releases", "../releases"]
            inspected = [{"Id": image_id, "Architecture": "amd64", "Config": {"Labels": {
                "org.opencontainers.image.revision": revision}}}]
            previous = Path.cwd()
            try:
                os.chdir(maintenance)
                with patch.object(sys, "argv", argv), patch.dict(os.environ), \
                     patch.object(promote_release, "fingerprint", return_value=evidence), \
                     patch.object(promote_release.subprocess, "run"), \
                     patch.object(promote_release.subprocess, "check_output", return_value=json.dumps(inspected).encode()), \
                     patch.object(promote_release, "urlopen", return_value=io.BytesIO(json.dumps({"revision": revision}).encode())):
                    promote_release.main()
            finally:
                os.chdir(previous)
            self.assertEqual(current.resolve(), releases / revision)
            self.assertFalse((releases / "current").exists())
            self.assertTrue(old.is_dir())

    def test_checksum_and_approved_revision_are_required_before_loading_image(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            revision = "a" * 40
            for name in ("image.tar.gz", "source.tar.gz"):
                (root / name).write_bytes(b"package-content")
            data = {"revision": revision, "image": "ghcr.io/example/aeris:sha-" + revision,
                    "os": "linux", "architecture": "amd64",
                    "files": {name: database_backup.digest_file(root / name) for name in ("image.tar.gz", "source.tar.gz")}}
            (root / "release.json").write_text(json.dumps(data))
            self.assertEqual(promote_release.validate_bundle(root, revision), data)
            with self.assertRaisesRegex(ValueError, "approved"):
                promote_release.validate_bundle(root, "b" * 40)
            (root / "image.tar.gz").write_bytes(b"altered-content")
            with self.assertRaisesRegex(ValueError, "checksum"):
                promote_release.validate_bundle(root, revision)

    def test_source_archive_cannot_escape_destination_or_create_links(self):
        for name, kind in (("../escaped", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                archive = root / "source.tar.gz"
                with tarfile.open(archive, "w:gz") as stream:
                    entry = tarfile.TarInfo(name)
                    entry.type = kind
                    entry.linkname = "../escaped"
                    entry.size = 1 if kind == tarfile.REGTYPE else 0
                    stream.addfile(entry, io.BytesIO(b"x") if entry.size else None)
                destination = root / "release"
                destination.mkdir()
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    promote_release.extract_source(archive, destination)
                self.assertEqual(list(destination.iterdir()), [])
                self.assertFalse((root / "escaped").exists())

    def test_restore_failure_cleans_only_its_generated_test_database(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "aeris.dump"
            archive.write_bytes(b"synthetic-dump")
            archive.chmod(0o600)
            manifest = root / "aeris.json"
            database_backup.private_json(manifest, {"archive": archive.name, "database": "aeris",
                "compose_project": "aeris-shared", "archive_sha256": database_backup.digest_file(archive), "evidence": {}})
            seen = []
            def execute(compose, *args, **kwargs):
                seen.append(args)
                if args[0] == "pg_restore":
                    raise RuntimeError("Synthetic restore failure")
            with patch.object(database_backup, "database_command", side_effect=execute):
                with self.assertRaisesRegex(RuntimeError, "Synthetic restore"):
                    database_backup.verify_restore([], manifest)
            created, restore, dropped = seen
            target = created[-1]
            self.assertTrue(target.startswith("aeris_restore_") and target.endswith("_test"))
            self.assertEqual(restore[restore.index("-d") + 1], target)
            self.assertEqual(dropped[-1], target)
            self.assertNotEqual(target, "aeris")
            self.assertFalse(manifest.with_suffix(".verified.json").exists())

    def test_altered_backup_is_rejected_before_any_database_command(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "aeris.dump"
            archive.write_bytes(b"original")
            archive.chmod(0o600)
            manifest = root / "aeris.json"
            database_backup.private_json(manifest, {"archive": archive.name, "database": "aeris",
                "archive_sha256": database_backup.digest_file(archive)})
            archive.write_bytes(b"changed")
            with patch.object(database_backup, "database_command") as command:
                with self.assertRaisesRegex(ValueError, "checksum"):
                    database_backup.verify_restore([], manifest)
                command.assert_not_called()

    def test_unverified_or_wrong_project_backup_cannot_authorize_promotion(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "verification.json"
            for project, verified in (("another-project", True), ("aeris-shared", False)):
                path.write_text(json.dumps({"verified_at": datetime.now(timezone.utc).isoformat(),
                    "compose_project": project, "database": "aeris", "restored_into_isolated_database": verified}))
                path.chmod(0o600)
                with self.assertRaisesRegex(ValueError, "recent verified"):
                    promote_release.require_backup(path)


if __name__ == "__main__":
    unittest.main()

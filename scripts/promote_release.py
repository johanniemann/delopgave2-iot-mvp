"""Promote a verified tested image, preserving the shared database and certificates."""
import argparse
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from urllib.request import urlopen

from database_backup import digest_file, fingerprint


def validate_bundle(bundle, revision):
    data = json.loads((bundle / "release.json").read_text())
    if not re.fullmatch(r"[a-f0-9]{40}", revision) or data["revision"] != revision:
        raise ValueError("Select the separately approved full source commit.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9./_-]*:sha-" + revision, data["image"]):
        raise ValueError("Release image must be tagged with the exact source commit.")
    if data["os"] != "linux" or data["architecture"] not in {"amd64", "arm64"}:
        raise ValueError("Unsupported image platform.")
    if set(data["files"]) != {"source.tar.gz", "image.tar.gz"}:
        raise ValueError("Unexpected release file set.")
    for name, expected in data["files"].items():
        if digest_file(bundle / name) != expected:
            raise ValueError("Release checksum mismatch; no deployment performed.")
    return data


def extract_source(archive, destination):
    with tarfile.open(archive) as source:
        for item in source.getmembers():
            target = (destination / item.name).resolve()
            if (not target.is_relative_to(destination.resolve()) or item.name.startswith("/")
                    or not (item.isfile() or item.isdir())):
                raise ValueError("Unsafe source archive entry; no extraction performed.")
        source.extractall(destination, filter="data")


def require_backup(path):
    if path.stat().st_mode & 0o077:
        raise ValueError("Backup verification must be private.")
    data = json.loads(path.read_text())
    age = datetime.now(timezone.utc) - datetime.fromisoformat(data["verified_at"])
    if (data.get("compose_project") != "aeris-shared" or data.get("database") != "aeris"
            or data.get("restored_into_isolated_database") is not True
            or not timedelta(0) <= age < timedelta(hours=24)):
        raise ValueError("A recent verified restore of the shared database is required.")
    # A successful restore is evidence only while its exact private archive remains usable.
    name = data.get("archive")
    if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.dump", name)
            or not re.fullmatch(r"[a-f0-9]{64}", data.get("archive_sha256", ""))):
        raise ValueError("Verify a named backup archive with the current maintenance tools before promotion.")
    archive = path.parent / name
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("The verified backup archive is missing or is not a regular file.")
    if archive.stat().st_mode & 0o077 or digest_file(archive) != data["archive_sha256"]:
        raise ValueError("Verified backup privacy/checksum validation failed; no deployment performed.")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--backup-verification", type=Path, required=True)
    parser.add_argument("--releases", type=Path, required=True)
    args = parser.parse_args()
    bundle, env_file = args.bundle.resolve(), args.env_file.resolve(strict=True)
    if env_file.stat().st_mode & 0o077:
        parser.error("Shared settings must be owner-readable only.")
    data = validate_bundle(bundle, args.revision)
    backup = require_backup(args.backup_verification.resolve())
    releases = args.releases.resolve()
    destination = releases / args.revision
    if destination.exists():
        parser.error("This release directory exists; inspect it before attempting another promotion.")
    destination.mkdir(parents=True)
    extract_source(bundle / "source.tar.gz", destination)
    (destination / "RELEASE_COMMIT").write_text(args.revision + "\n")
    compose = ["docker", "compose", "--project-name", "aeris-shared", "--env-file", str(env_file),
               "-f", "compose.yaml", "-f", "compose.shared.yaml", "-f", "compose.release.yaml"]
    previous = Path.cwd()
    os.chdir(destination)
    # The DB service/project is already running; fingerprint() invokes Compose from ROOT.
    # Resolve file paths so the current script location cannot redirect the shared target.
    compose = [str(destination / p) if p in {"compose.yaml", "compose.shared.yaml", "compose.release.yaml"} else p for p in compose]
    environment = dict(os.environ, AERIS_RELEASE_IMAGE=data["image"])
    os.environ["AERIS_RELEASE_IMAGE"] = data["image"]
    try:
        if fingerprint(compose, "aeris") != backup["evidence"]:
            raise ValueError("Shared evidence changed since backup. Create and verify a fresh backup before promotion.")
        subprocess.run(["docker", "image", "load", "--input", str(bundle / "image.tar.gz")], check=True)
        image = json.loads(subprocess.check_output(["docker", "image", "inspect", data["image"]]))[0]
        if (image["Id"] != data["image_id"] or image["Architecture"] != data["architecture"]
                or image["Config"].get("Labels", {}).get("org.opencontainers.image.revision") != args.revision):
            raise ValueError("Loaded image differs from the tested release.")
        def run(*parts):
            subprocess.run(compose + list(parts), cwd=destination, env=environment, check=True, stdin=subprocess.DEVNULL)
        run("config", "--quiet")
        run("run", "--rm", "--no-deps", "caddy", "caddy", "validate", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile")
        run("up", "-d", "--no-build", "--pull", "never", "--wait", "--wait-timeout", "180", "caddy")
        with urlopen("http://127.0.0.1:8765/health", timeout=10) as response:
            if json.load(response)["revision"] != args.revision:
                raise ValueError("Running API revision does not match the selected release.")
        after = fingerprint(compose, "aeris")
        for table, expected in backup["evidence"]["tables"].items():
            if table != "schema_versions" and after["tables"].get(table) != expected:
                raise ValueError("Pre-existing database evidence changed during promotion.")
        (destination / "release.json").write_text(json.dumps(data, indent=2) + "\n")
        current = releases.parent / "current"
        if current.exists() and not current.is_symlink():
            raise ValueError("Current release pointer is not a symlink; inspect before replacing it.")
        temporary = current.with_name(".current-" + args.revision[:12])
        temporary.symlink_to(destination)
        temporary.replace(current)
        print("Tested image promoted. Existing domain/account evidence preserved. Complete external HTTPS/account verification next.")
    finally:
        os.chdir(previous)


if __name__ == "__main__":
    main()

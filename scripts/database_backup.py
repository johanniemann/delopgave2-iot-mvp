"""Private PostgreSQL backup plus verified restore into a new disposable database."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def private_json(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(data, stream, indent=2)


def digest_file(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def database_command(compose, *arguments, **kwargs):
    result = subprocess.run(compose + ["exec", "-T", "db", *arguments],
                            cwd=ROOT, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        raise RuntimeError(f"Database operation failed (exit {result.returncode}); no database content printed.")
    return result


def fingerprint(compose, database):
    def query(sql):
        return database_command(compose, "psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", "prototype",
                                "-d", database, "-At", "-c", sql, stdout=subprocess.PIPE).stdout.decode().strip()
    tables = query("SELECT tablename FROM pg_tables WHERE schemaname='aeris' ORDER BY tablename").splitlines()
    if not tables:
        raise RuntimeError("No Aeris schema found; refusing an empty verification.")
    value = hashlib.sha256()
    counts = {}
    table_hashes = {}
    for table in tables:
        # Sessions/throttles are transient and may change on read-only HTTP checks.
        if table in {"sessions", "login_limits"}:
            continue
        if not re.fullmatch(r"[a-z_]+", table):
            raise RuntimeError("Unexpected database table name.")
        rows = json.loads(query(f"SELECT coalesce(jsonb_agg(r ORDER BY r::text),'[]'::jsonb) FROM (SELECT to_jsonb(t) r FROM aeris.{table} t) s"))
        counts[table] = len(rows)
        encoded = json.dumps([table, rows], sort_keys=True, separators=(",", ":")).encode()
        table_hashes[table] = hashlib.sha256(encoded).hexdigest()
        value.update(encoded)
    return {"sha256": value.hexdigest(), "counts": counts, "tables": table_hashes}


def backup(compose, directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.stat().st_mode & 0o077:
        raise ValueError("Backup directory must be private (chmod 700).")
    name = datetime.now(timezone.utc).strftime("aeris-%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
    archive = directory / (name + ".dump")
    before = fingerprint(compose, "aeris")
    descriptor = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        database_command(compose, "pg_dump", "-U", "prototype", "-d", "aeris", "-Fc", stdout=stream)
    after = fingerprint(compose, "aeris")
    if before != after:
        raise RuntimeError("Source changed during backup. Archive preserved, but no verified manifest created. Retry during a quiet window.")
    manifest = archive.with_suffix(".json")
    private_json(manifest, {"created_at": datetime.now(timezone.utc).isoformat(),
                           "compose_project": compose[compose.index("--project-name") + 1],
                           "database": "aeris", "archive": archive.name,
                           "archive_sha256": digest_file(archive), "evidence": before})
    return manifest


def verify_restore(compose, manifest):
    if manifest.stat().st_mode & 0o077:
        raise ValueError("Backup manifest must be private.")
    data = json.loads(manifest.read_text())
    if Path(data["archive"]).name != data["archive"] or data["database"] != "aeris":
        raise ValueError("Unexpected backup manifest.")
    archive = manifest.parent / data["archive"]
    if archive.stat().st_mode & 0o077 or digest_file(archive) != data["archive_sha256"]:
        raise ValueError("Backup privacy/checksum validation failed.")
    target = "aeris_restore_" + uuid4().hex + "_test"
    # target is always generated here; it can never be the live/demo database.
    database_command(compose, "createdb", "-U", "prototype", target, stdout=subprocess.DEVNULL)
    try:
        with archive.open("rb") as stream:
            database_command(compose, "pg_restore", "-U", "prototype", "-d", target,
                             "--no-owner", "--no-privileges", "--exit-on-error", stdin=stream, stdout=subprocess.DEVNULL)
        if fingerprint(compose, target) != data["evidence"]:
            raise RuntimeError("Restored evidence differs from the backup's source fingerprint.")
        result = manifest.with_suffix(".verified.json")
        private_json(result, {"verified_at": datetime.now(timezone.utc).isoformat(),
                              "compose_project": data["compose_project"], "database": data["database"],
                              "archive_sha256": data["archive_sha256"], "evidence": data["evidence"],
                              "restored_into_isolated_database": True})
        return result
    finally:
        database_command(compose, "dropdb", "-U", "prototype", target, stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "verify", "backup-and-verify"])
    parser.add_argument("--project", required=True)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--shared", action="store_true")
    parser.add_argument("--directory", type=Path, default=ROOT / ".codex-log/backups")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.project):
        parser.error("Use an explicit Compose project name.")
    if args.env_file.stat().st_mode & 0o077:
        parser.error("Environment settings must be private.")
    compose = ["docker", "compose", "--project-name", args.project, "--env-file", str(args.env_file.resolve()), "-f", "compose.yaml"]
    if args.shared:
        compose += ["-f", "compose.shared.yaml"]
    if args.action in {"backup", "backup-and-verify"}:
        result = backup(compose, args.directory.resolve())
        if args.action == "backup-and-verify":
            result = verify_restore(compose, result)
    else:
        if args.manifest is None:
            parser.error("verify requires --manifest from a completed backup.")
        result = verify_restore(compose, args.manifest.resolve())
    print(result)
    print("Private backup created." if args.action == "backup" else "Isolated restore matches saved domain/account evidence. Transient sessions/throttles are excluded from comparison.")


if __name__ == "__main__":
    main()

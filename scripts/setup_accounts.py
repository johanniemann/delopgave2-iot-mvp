"""Provision first local demo accounts; preserve existing credentials and user data."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed", action="store_true", help="Use the isolated port-8766 observability demo")
    args = parser.parse_args()
    if args.observed:
        from observability import compose
        def command(*parts, **kwargs):
            return compose("app", *parts, **kwargs)
        port = command("port", "app", "8000", capture=True).stdout.strip()
    else:
        def command(*parts, **kwargs):
            capture = kwargs.pop("capture", False)
            return subprocess.run(["docker", "compose", *parts], cwd=ROOT, check=True,
                                  capture_output=capture, text=True, **kwargs)
        port = command("port", "app", "8000", capture=True).stdout.strip()
    if not port.startswith("127.0.0.1:") or not port.split(":")[-1].isdigit():
        raise SystemExit("Refusing setup: the selected app must be bound only to loopback.")
    base = "http://" + port
    with urlopen(base + "/health", timeout=10) as response:
        if json.load(response)["mode"] != "local":
            raise SystemExit("Use the privileged host-side bootstrap for a shared deployment.")
    target = ROOT / (".env.accounts-" + port.split(":")[-1] + ".json")
    if target.exists():
        print(f"Existing private {target.name} preserved. No accounts changed.")
        return
    data = {"base_url": base,
            "admin": {"username": "admin", "display_name": "Local Administrator", "role": "admin", "password": secrets.token_urlsafe(24)},
            "technician": {"username": "technician", "display_name": "Demo Technician", "role": "technician", "password": secrets.token_urlsafe(24)}}
    # Write privately before the transaction so a local interruption cannot lose
    # the only copy of the initial credentials. Preserve it even on an interrupted
    # command: the database commit may already have succeeded.
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)
    try:
        command("exec", "-T", "app", "/app/.venv/bin/python", "-m", "app.accounts", input=json.dumps(data))
    except BaseException:
        print(f"Setup interrupted/failed. Private {target.name} preserved; check the result before retrying.")
        raise
    print(f"Local Admin and Technician ready. Credentials are only in ignored {target.name} (owner-readable).")
    print("These are local demo accounts. Each teammate gets their own local installation; never commit/share this file.")


if __name__ == "__main__":
    main()

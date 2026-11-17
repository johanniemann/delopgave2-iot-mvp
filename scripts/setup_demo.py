"""Create ignored local-only demo settings without printing credentials."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import socket

ROOT = Path(__file__).resolve().parents[1]


def local_project(root):
    identity = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:12]
    return "aeris-local-" + identity


def port_number(value):
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("Use an integer port from 1 to 65535.") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Use an integer port from 1 to 65535.")
    return port


def project_name(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        raise argparse.ArgumentTypeError("Use a lowercase Compose project name: letters, digits, hyphens or underscores.")
    if value == "aeris-shared":
        raise argparse.ArgumentTypeError("aeris-shared is reserved for the explicit shared deployment, not new local settings.")
    return value


def main(argv=None):
    target = ROOT / ".env"
    if target.exists():
        print("Existing .env preserved, including its project, port and credentials. No overrides applied.")
        return

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=port_number, default=os.environ.get("APP_PORT", "8765"),
                        help="Unused local port for new settings (APP_PORT or 8765 by default)")
    parser.add_argument("--project", type=project_name,
                        default=os.environ.get("COMPOSE_PROJECT_NAME", local_project(ROOT)),
                        help="New local Compose project (explicit environment value or checkout-specific name)")
    args = parser.parse_args(argv)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", args.port))
    except OSError as exc:
        raise SystemExit(f"Local port {args.port} is unavailable. Choose an unused port with --port, then retry setup.") from exc

    content = (f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
               f"APP_MODE=local\nAPP_PORT={args.port}\n"
               f"COMPOSE_PROJECT_NAME={args.project}\n")
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
    except FileExistsError:
        print("Existing .env preserved.")
        return
    print("Created ignored .env for the local demo. No credentials were printed.")
    print(f"Local project: {args.project}; dashboard: http://localhost:{args.port}.")


if __name__ == "__main__":
    main()

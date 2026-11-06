"""Create private settings on the shared host; never print or overwrite secrets."""
import argparse
import ipaddress
import os
from pathlib import Path
import re
import secrets


def hostname(value):
    value = value.lower().rstrip(".")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise argparse.ArgumentTypeError("Use a public DNS hostname, not an IP address.")
    labels = value.split(".")
    if (len(value) > 253 or len(labels) < 2
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)):
        raise argparse.ArgumentTypeError("Use the configured public DNS hostname without a scheme or path.")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hostname", type=hostname)
    parser.add_argument("--env-file", type=Path, default=Path(".env.shared"))
    args = parser.parse_args()
    content = (f"AERIS_HOSTNAME={args.hostname}\n"
               f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
               f"API_TOKEN={secrets.token_urlsafe(32)}\n"
               "APP_MODE=shared\nAPP_PORT=8765\n")
    try:
        descriptor = os.open(args.env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.exit(1, "Existing settings preserved. Reuse them; do not regenerate a database password.\n")
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(content)
    print("Created private shared settings. No credentials were printed.")


if __name__ == "__main__":
    main()

"""Run the saved collection with private runtime credentials, never command arguments."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile

from api_client import ROOT, ApiClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    base = f"http://127.0.0.1:{args.port}"
    ApiClient(base)  # reject unsafe target formats before reading credentials
    source = ROOT / f".env.accounts-{args.port}.json"
    data = json.loads(source.read_text())
    if data["base_url"] != base or (os.name != "nt" and source.stat().st_mode & 0o077):
        raise SystemExit("Use the private credentials belonging to this exact local app.")
    tech = data["technician"]
    with tempfile.TemporaryDirectory(prefix="aeris-postman-") as folder:
        environment = Path(folder) / "private-environment.json"
        with environment.open("x") as stream:
            environment.chmod(0o600)
            json.dump({"name": "Private local runtime", "values": [
                {"key": "base_url", "value": base, "enabled": True},
                {"key": "login_username", "value": tech["username"], "enabled": True},
                {"key": "login_password", "value": tech["password"], "enabled": True}]}, stream)
        result = subprocess.run([shutil.which("npx") or "npx", "--yes", "newman@6.2.3", "run", "postman/Aeris.postman_collection.json",
                                 "-e", str(environment)], cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()

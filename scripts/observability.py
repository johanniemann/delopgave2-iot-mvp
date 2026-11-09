"""Start/stop an isolated local SigNoz demo; never operates the Azure VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import ssl
import sys
import subprocess
import tarfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".codex-log" / "observability"
ENV = ROOT / ".env.observability"
FOUNDRY_VERSION = "0.5.0"
FOUNDRY_HASHES = {
    "darwin_arm64": "00bb738457239ef6dce3844964214c9a10182cc2dde670ff071edb0752e69115",
    "darwin_amd64": "18f83860602ac0a4ef05e8b51901945d155a71b2932af369e2ad6a73bf414b1d",
    "linux_arm64": "0482f952b706c46d4030df825bf6abde7cadacde4a35d121ab93098025e7a194",
    "linux_amd64": "b2f21e0cf12e9fa0f32dcaf414ec97823b32a29c3252bee23b896d158af2c650",
}
STACK = RUNTIME / "pours" / "deployment" / "compose.yaml"
BASE = "http://127.0.0.1:8766"
_client = None


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def compose(project, *arguments, capture=False, **kwargs):
    if project == "monitoring":
        command = ["docker", "compose", "-p", "aeris-monitoring", "-f", str(STACK)]
    else:
        command = ["docker", "compose", "-p", "aeris-observed", "--env-file", str(ENV),
                   "-f", str(ROOT / "compose.yaml"), "-f", str(ROOT / "compose.observability.yaml")]
    # Do not let an inherited shell variable redirect the local demonstration.
    environment = dict(os.environ)
    for key in ("APP_PORT", "APP_MODE", "API_TOKEN", "POSTGRES_PASSWORD", "COMPOSE_PROJECT_NAME",
                "DATABASE_URL", "AERIS_OTLP_ENDPOINT", "PUBLIC_ORIGIN", "ALLOWED_HOSTS"):
        environment.pop(key, None)
    environment.update(APP_PORT="8766", APP_MODE="local")
    return run(command + list(arguments), env=environment, capture_output=capture, text=True, **kwargs)


def prepare():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if not ENV.exists():
        with ENV.open("x", encoding="utf-8") as stream:
            ENV.chmod(0o600)
            stream.write(f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
                         "APP_MODE=local\nAPP_PORT=8766\n")
    host = platform.system().lower()
    arch = {"aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine(), platform.machine())
    key = host + "_" + arch
    if key not in FOUNDRY_HASHES:
        raise SystemExit("Use macOS or Linux. On Windows use WSL 2 with native Docker; see the guide.")
    archive = RUNTIME / f"foundry_{key}.tar.gz"
    if not archive.exists():
        print("Downloading official Foundry 0.5.0; verifying the pinned SHA-256.", flush=True)
        context = ssl.create_default_context(cafile="/etc/ssl/cert.pem" if host == "darwin" else None)
        url = f"https://github.com/SigNoz/foundry/releases/download/v{FOUNDRY_VERSION}/foundry_{key}.tar.gz"
        with urlopen(url, context=context, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != FOUNDRY_HASHES[key]:
            raise SystemExit("Foundry checksum mismatch; nothing executed.")
        archive.write_bytes(data)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != FOUNDRY_HASHES[key]:
        raise SystemExit("Foundry checksum mismatch; nothing executed.")
    # Extract only the expected executable, never arbitrary archive paths/links.
    binary = RUNTIME / "foundryctl"
    with tarfile.open(archive) as bundle:
        entry = bundle.getmember(f"foundry_{key}/bin/foundryctl")
        if not entry.isfile():
            raise SystemExit("Unexpected Foundry archive entry.")
        binary.write_bytes(bundle.extractfile(entry).read())
    binary.chmod(0o700)
    # Foundry writes a resolved .lock beside its input; keep that generated file
    # in ignored runtime storage as well as the rendered Compose configuration.
    casting = RUNTIME / "casting.yaml"
    casting.write_bytes((ROOT / "ops/observability/casting.yaml").read_bytes())
    run([str(binary), "--no-ledger", "--no-updater", "forge", "-f",
         str(casting), "-p", str(RUNTIME / "pours")])


def get(path):
    global _client
    if _client is None:
        from api_client import ApiClient
        _client = ApiClient(BASE)
        _client.login()
    return _client.request(path)


def traffic():
    require_local_app()
    for _ in range(30):
        status, _ = get("/api/overview")
        if status != 200:
            raise SystemExit(f"Expected local overview 200, received {status}.")
        time.sleep(0.1)
    print("30 successful local API requests generated. Allow 10 seconds for export.")


def failure_demo():
    # Only the deliberately separate aeris-observed DB is stopped, never the
    # original local project, shared VM or a user-supplied host/database name.
    require_local_app()
    status, payload = get("/api/overview")
    if status != 200:
        raise SystemExit("Start the isolated local demo first.")
    cases = json.loads(payload)["cases"]
    if not cases:
        raise SystemExit("This demo requires a saved case to verify preservation.")
    path = "/api/cases/" + cases[0]["id"]
    _, before = get(path)
    try:
        compose("app", "stop", "db")
        for _ in range(5):
            status, _ = get("/api/overview")
            if status != 503:
                raise RuntimeError(f"Expected database-unavailable 503, received {status}.")
            time.sleep(1)
        print("Five expected HTTP 503 responses recorded for the local alarm test.")
    finally:
        compose("app", "up", "-d", "--wait", "db")
    for _ in range(30):
        try:
            status, after = get(path)
            if status == 200:
                if after != before:
                    raise RuntimeError("Saved case response changed during the test.")
                print("Database restored; HTTP 200 and the unchanged complete saved case verified.")
                return
        except (URLError, TimeoutError):
            pass
        time.sleep(1)
    raise SystemExit("Database started, but API recovery was not observed within 30 seconds.")


def require_local_app():
    port = compose("app", "port", "app", "8000", capture=True).stdout.strip()
    if port != "127.0.0.1:8766":
        raise SystemExit("Refusing the test: the isolated app must own 127.0.0.1:8766.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "stop", "status", "traffic", "failure-demo"])
    action = parser.parse_args().action
    if action == "up":
        prepare()
        compose("monitoring", "up", "-d", "--wait", "--wait-timeout", "240",
                "ingester", "signoz-signoz-0")
        compose("app", "up", "-d", "--build", "--wait", "app")
        run([sys.executable, "scripts/setup_accounts.py", "--observed"])
        print("Aeris: http://localhost:8766 | SigNoz: http://localhost:3301")
    elif action == "stop":
        if ENV.exists():
            compose("app", "stop", "app", "db")
        if STACK.exists():
            compose("monitoring", "stop")
        print("Local demo stopped. All database/telemetry volumes preserved. Azure unchanged.")
    elif action == "status":
        if ENV.exists():
            compose("app", "ps", "-a")
        if STACK.exists():
            compose("monitoring", "ps", "-a")
    elif action == "traffic":
        traffic()
    else:
        failure_demo()


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"Command failed with exit code {error.returncode}; see output above.") from None

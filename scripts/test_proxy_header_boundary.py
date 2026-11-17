"""Opt-in Caddy integration check; importing this module never starts Docker.

Run: python3 scripts/test_proxy_header_boundary.py --output /tmp/caddy-proof.json
Uses existing pinned images, an internal network, no host ports and no DB volumes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[1]
ECHO_BACKEND = r"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

class Echo(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({
            'x_real_ip': self.headers.get_all('X-Real-IP', []),
            'x_forwarded_for': self.headers.get_all('X-Forwarded-For', []),
            'backend_peer': self.client_address[0],
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

ThreadingHTTPServer(('0.0.0.0', 8000), Echo).serve_forever()
"""
CLIENT = r"""
import http.client
import json
import socket
import time

cases = [
    ('no_forwarded_headers', []),
    ('forged_real_ip', [('X-Real-IP', '198.51.100.1')]),
    ('duplicate_real_ip', [('X-Real-IP', '198.51.100.1'),
                           ('X-Real-IP', '203.0.113.2')]),
    ('mixed_case_real_ip', [('x-real-ip', '198.51.100.1'),
                            ('X-REAL-IP', '203.0.113.2')]),
    ('comma_real_ip', [('X-Real-IP', '198.51.100.1, 203.0.113.2')]),
    ('forged_forwarded_for', [('X-Forwarded-For', '198.51.100.1')]),
    ('duplicate_both', [('X-Real-IP', '198.51.100.1'),
                        ('X-Real-IP', '203.0.113.2'),
                        ('X-Forwarded-For', '198.51.100.3'),
                        ('x-forwarded-for', '203.0.113.4, 198.51.100.5')]),
    ('other_forwarded_claims', [('Forwarded', 'for=198.51.100.6;proto=https'),
                               ('X-Real-IP', '198.51.100.7'),
                               ('X-Forwarded-For', '203.0.113.8')]),
]

def request(headers):
    with socket.create_connection(('proxy', 8080), timeout=5) as sock:
        source_ip = sock.getsockname()[0]
        lines = ['GET / HTTP/1.1', 'Host: proxy:8080', 'Connection: close']
        lines.extend(name + ': ' + value for name, value in headers)
        sock.sendall(('\r\n'.join(lines) + '\r\n\r\n').encode('ascii'))
        response = http.client.HTTPResponse(sock)
        response.begin()
        payload = response.read()
        if response.status != 200:
            raise RuntimeError('Echo endpoint returned HTTP ' + str(response.status))
        return source_ip, json.loads(payload)

for attempt in range(50):
    try:
        request([])
        break
    except (OSError, RuntimeError, http.client.HTTPException):
        if attempt == 49:
            raise
        time.sleep(0.1)

results = []
for name, headers in cases:
    source_ip, received = request(headers)
    results.append({'case': name, 'sent_headers': headers,
                    'socket_source_ip': source_ip, **received})
print(json.dumps(results))
"""


def docker(*arguments, check=True):
    result = subprocess.run(
        ["docker", *arguments], text=True, capture_output=True,
        timeout=40, check=False,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "Docker command failed")
    return result


def pinned_image(path, pattern):
    match = re.search(pattern, path.read_text(), re.MULTILINE)
    if not match:
        raise RuntimeError(f"No expected digest-pinned image in {path.name}")
    reference = match.group(1)
    # Inspect only: missing images fail instead of pulling from a registry.
    image_id = docker("image", "inspect", reference, "--format", "{{.Id}}").stdout.strip()
    return {"reference": reference, "id": image_id}


def container_ip(container_id, network_name):
    inspected = json.loads(docker("container", "inspect", container_id).stdout)[0]
    return inspected["NetworkSettings"]["Networks"][network_name]["IPAddress"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional local JSON evidence file")
    args = parser.parse_args(argv)
    run_id = "aeris-proxy-qa-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8]
    source = (ROOT / "ops/Caddyfile").read_bytes()
    proof = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Isolated local HTTP proxy boundary; not live Azure or public TLS verification",
        "run_id": run_id,
        "caddyfile_sha256": hashlib.sha256(source).hexdigest(),
        "caddyfile": source.decode(),
        "official_references": [
            "https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#headers",
            "https://caddyserver.com/docs/caddyfile/concepts#placeholders",
        ],
        "clients": [], "passed": False, "cleanup": [],
    }
    containers = []
    network_id = None
    try:
        python = pinned_image(ROOT / "Dockerfile", r"^FROM\s+(python:\S+@sha256:[0-9a-f]{64})\b")
        caddy = pinned_image(ROOT / "compose.shared.yaml", r"^\s+image:\s+(caddy:\S+@sha256:[0-9a-f]{64})\s*$")
        proof["images"] = {"python": python, "caddy": caddy}
        network_id = docker("network", "create", "--internal", "--label", "aeris.qa.proxy=" + run_id, run_id).stdout.strip()
        with tempfile.TemporaryDirectory(prefix="aeris-proxy-qa-") as temporary:
            temporary = Path(temporary)
            (temporary / "Caddyfile").write_bytes(source)
            (temporary / "echo.py").write_text(ECHO_BACKEND)

            def start(suffix, image_id, command=(), extra=()):
                result = docker(
                    "create", "--pull", "never", "--name", run_id + "-" + suffix,
                    "--label", "aeris.qa.proxy=" + run_id,
                    "--network", network_id, "--read-only", "--cap-drop", "ALL",
                    "--security-opt", "no-new-privileges=true",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", *extra,
                    image_id, *command,
                )
                identifier = result.stdout.strip()
                containers.append(identifier)
                docker("start", identifier)
                return identifier

            backend = start("backend", python["id"], ("python", "/qa/echo.py"), (
                "--network-alias", "app", "--mount",
                f"type=bind,src={temporary / 'echo.py'},dst=/qa/echo.py,readonly",
            ))
            proxy = start("proxy", caddy["id"], extra=(
                "--network-alias", "proxy", "--env", "AERIS_HOSTNAME=http://proxy:8080",
                "--tmpfs", "/data:rw,noexec,nosuid,size=16m",
                "--tmpfs", "/config:rw,noexec,nosuid,size=16m",
                "--mount", f"type=bind,src={temporary / 'Caddyfile'},dst=/etc/caddy/Caddyfile,readonly",
            ))
            proof["caddy_version"] = docker("exec", proxy, "caddy", "version").stdout.strip()
            proof["proxy_ip"] = container_ip(proxy, run_id)
            proof["backend_ip"] = container_ip(backend, run_id)
            for label in ("client-a", "client-b"):
                client = start(label, python["id"], ("python", "-c", "import time; time.sleep(300)"))
                results = json.loads(docker("exec", client, "python", "-c", CLIENT).stdout)
                client_ip = container_ip(client, run_id)
                for result in results:
                    result["passed"] = (
                        result["socket_source_ip"] == client_ip
                        and result["x_real_ip"] == [client_ip]
                        and result["x_forwarded_for"] == [client_ip]
                        and result["backend_peer"] == proof["proxy_ip"]
                    )
                proof["clients"].append({"name": label, "ip": client_ip, "results": results})
            proof["passed"] = (
                len({client["ip"] for client in proof["clients"]}) == 2
                and all(result["passed"] for client in proof["clients"] for result in client["results"])
            )
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        proof["error"] = str(error)
    finally:
        # Remove only IDs successfully created by this run. Never remove volumes.
        for identifier in reversed(containers):
            result = docker("container", "rm", "--force", identifier, check=False)
            proof["cleanup"].append({"kind": "container", "id": identifier, "removed": result.returncode == 0})
        if network_id:
            result = docker("network", "rm", network_id, check=False)
            proof["cleanup"].append({"kind": "network", "id": network_id, "removed": result.returncode == 0})
        proof["passed"] = proof["passed"] and all(item["removed"] for item in proof["cleanup"])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proof, indent=2) + "\n")
        print("Proxy boundary evidence saved to", args.output)
    else:
        print(json.dumps(proof, indent=2))
    total = sum(len(client["results"]) for client in proof["clients"])
    if "error" in proof:
        print("Proxy boundary setup/check failed:", proof["error"])
    print(f"Proxy boundary: {'PASS' if proof['passed'] else 'FAIL'} ({total} requests, two isolated clients)")
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

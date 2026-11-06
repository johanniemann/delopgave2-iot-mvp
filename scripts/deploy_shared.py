"""Deploy this checked-out release on the existing Docker host, preserving volumes."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    env_file = args.env_file.resolve(strict=True)
    if env_file.stat().st_mode & 0o077:
        parser.error("Shared settings must be private: chmod 600 the environment file.")
    root = Path(__file__).resolve().parents[1]
    compose = ["docker", "compose", "--project-name", "aeris-shared", "--env-file", str(env_file),
               "-f", "compose.yaml", "-f", "compose.shared.yaml"]
    # Docker must not consume the remaining commands when invoked over SSH stdin.
    subprocess.run(compose + ["config", "--quiet"], cwd=root, check=True, stdin=subprocess.DEVNULL)
    subprocess.run(compose + ["run", "--rm", "--no-deps", "caddy", "caddy", "validate",
                              "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"], cwd=root, check=True, stdin=subprocess.DEVNULL)
    subprocess.run(compose + ["up", "-d", "--build", "--wait", "--wait-timeout", "180", "caddy"], cwd=root, check=True, stdin=subprocess.DEVNULL)
    subprocess.run(compose + ["ps"], cwd=root, check=True, stdin=subprocess.DEVNULL)
    print("Containers are ready. Verify trusted public HTTPS and the access guard before sharing the URL.")


if __name__ == "__main__":
    main()

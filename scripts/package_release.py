"""Package the tested runtime image and its exact committed source for promotion."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from database_backup import digest_file

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    revision = run("git", "rev-parse", "HEAD")
    if not re.fullmatch(r"[a-f0-9]{40}", revision) or run("git", "status", "--porcelain"):
        parser.error("Commit all release source first; packaging requires a clean checkout.")
    image = json.loads(run("docker", "image", "inspect", args.image))[0]
    if image["Config"].get("Labels", {}).get("org.opencontainers.image.revision") != revision:
        parser.error("Runtime image label must match this exact source commit.")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source.tar.gz"
    subprocess.run(["git", "archive", "--format=tar.gz", "--output", str(source), revision], cwd=ROOT, check=True)
    archive = output / "image.tar.gz"
    process = subprocess.Popen(["docker", "image", "save", args.image], stdout=subprocess.PIPE)
    try:
        with archive.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
            shutil.copyfileobj(process.stdout, stream)
    finally:
        process.stdout.close()
    if process.wait() != 0:
        raise SystemExit("Image export failed; do not promote this incomplete package.")
    manifest = {"revision": revision, "image": args.image, "image_id": image["Id"],
                "os": image["Os"], "architecture": image["Architecture"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "files": {p.name: digest_file(p) for p in (source, archive)}}
    (output / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Packaged tested image {image['Id']} and source {revision} in {output}.")


if __name__ == "__main__":
    main()

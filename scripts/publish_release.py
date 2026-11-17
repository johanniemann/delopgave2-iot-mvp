"""Publish only the exact runtime image already tested and packaged by CI."""
import argparse
import json
from pathlib import Path
import subprocess

from promote_release import validate_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    data = validate_bundle(args.bundle, args.revision)
    subprocess.run(["docker", "image", "load", "--input", str(args.bundle / "image.tar.gz")], check=True)
    actual = json.loads(subprocess.check_output(["docker", "image", "inspect", data["image"]]))[0]
    if actual["Id"] != data["image_id"]:
        raise SystemExit("Loaded image does not match the tested artifact.")
    subprocess.run(["docker", "push", data["image"]], check=True)


if __name__ == "__main__":
    main()

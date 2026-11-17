"""Run locked SAST and runtime dependency audit; any failed check stops the gate."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    uv = ["uv", "run", "--frozen", "--group", "security"]
    subprocess.run(uv + ["bandit", "-r", "app", "-ll", "-ii"], cwd=ROOT, check=True)
    with tempfile.TemporaryDirectory(prefix="aeris-audit-") as folder:
        requirements = str(Path(folder) / "runtime.txt")
        subprocess.run(["uv", "export", "--quiet", "--frozen", "--no-dev", "--no-emit-project",
                        "--format", "requirements-txt", "--output-file", requirements], cwd=ROOT, check=True)
        subprocess.run(uv + ["pip-audit", "--require-hashes", "--disable-pip", "-r", requirements], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

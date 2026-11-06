"""Create ignored local-only demo settings without printing credentials."""
from pathlib import Path
import secrets


def main():
    target = Path(__file__).resolve().parents[1] / ".env"
    if target.exists():
        print("Existing .env preserved. Local prototype settings are ready.")
        return
    content = (f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
               f"API_TOKEN={secrets.token_urlsafe(32)}\n"
               "APP_MODE=local\nAPP_PORT=8765\n")
    try:
        with target.open("x", encoding="utf-8") as stream:
            target.chmod(0o600)
            stream.write(content)
    except FileExistsError:
        print("Existing .env preserved.")
        return
    print("Created ignored .env for the local demo. No credentials were printed.")


if __name__ == "__main__":
    main()

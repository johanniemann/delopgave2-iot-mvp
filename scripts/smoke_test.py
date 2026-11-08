"""Check the actual HTTP application, authentication and saved evidence."""
import json
import os

from api_client import ApiClient


def main():
    base = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
    shared = os.environ.get("SMOKE_EXPECT_SHARED", "false").lower() == "true"
    public_only = os.environ.get("SMOKE_PUBLIC_ONLY", "false").lower() == "true"
    client = ApiClient(base)

    def get(path):
        status, body = client.request(path)
        assert status == 200, f"{path}: expected 200, received {status}"
        return body

    health = json.loads(get("/health"))
    assert health["database"] == "connected"
    if shared:
        assert health["mode"] == "shared"
    assert client.request("/api/overview")[0] == 401
    assert b"Aeris" in get("/")
    assert b"function render" in get("/static/app.js")
    assert b"--green" in get("/static/styles.css")
    schema = json.loads(get("/openapi.json"))
    assert "/api/auth/login" in schema["paths"] and "/api/admin/users" in schema["paths"]
    if public_only:
        assert shared
        print("Shared public shell/readiness and anonymous API rejection passed. Cookie/TLS behavior is tested separately.")
        return
    client.login(credentials_file=os.environ.get("SMOKE_CREDENTIALS_FILE"))
    try:
        assert client.request("/api/admin/users")[0] == 403  # technician, even via direct HTTP
        overview = json.loads(get("/api/overview"))
        assert overview["simulation"] is True and overview["turbine_id"] == "WT-017"
        assert overview["scenarios"]
        assert json.loads(get("/api/scenarios/" + overview["active_scenario_id"]))["readings"]
    finally:
        client.logout()
    assert client.request("/api/overview")[0] == 401
    print("Live HTTP smoke passed: anonymous rejection, Technician login/admin denial, dashboard, PostgreSQL, OpenAPI and logout.")


if __name__ == "__main__":
    main()

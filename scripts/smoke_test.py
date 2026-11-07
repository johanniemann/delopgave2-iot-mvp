"""Check the actual running HTTP service, not the in-process test client."""
import json
import os
from urllib.error import HTTPError
import urllib.request


def main():
    base = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8765").rstrip("/")
    token = os.environ.get("SMOKE_API_TOKEN", "")
    shared = os.environ.get("SMOKE_EXPECT_SHARED", "false").lower() == "true"
    if shared and not token:
        raise SystemExit("A shared smoke check requires SMOKE_API_TOKEN; never put it in the URL.")

    def get(path):
        headers = {"Authorization": "Bearer " + token} if token and path.startswith("/api/") else {}
        request = urllib.request.Request(base + path, headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            assert response.status == 200
            return response.read()

    health = json.loads(get("/health"))
    assert health["database"] == "connected"
    if shared:
        assert health["mode"] == "shared"
        try:
            urllib.request.urlopen(base + "/api/overview", timeout=10)
        except HTTPError as response:
            assert response.code == 401
        else:
            raise AssertionError("Shared data was available without authentication.")
    overview = json.loads(get("/api/overview"))
    assert overview["simulation"] is True and overview["turbine_id"] == "WT-017"
    assert overview["scenarios"]
    sid = overview["active_scenario_id"]
    assert json.loads(get("/api/scenarios/" + sid))["readings"]
    assert b"Aeris" in get("/")
    assert b"function render" in get("/static/app.js")
    assert b"--green" in get("/static/styles.css")
    assert "/api/scenarios/{scenario_id}/review" in json.loads(get("/openapi.json"))["paths"]
    print("Live HTTP smoke check passed: dashboard, assets, API, PostgreSQL data and OpenAPI.")


if __name__ == "__main__":
    main()

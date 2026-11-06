"""Check the actual running HTTP service, not the in-process test client."""
import json
import os
import urllib.request


def main():
    base = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8765").rstrip("/")

    def get(path):
        with urllib.request.urlopen(base + path, timeout=10) as response:
            assert response.status == 200
            return response.read()

    assert json.loads(get("/health"))["database"] == "connected"
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

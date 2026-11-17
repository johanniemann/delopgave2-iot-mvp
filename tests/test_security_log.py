"""Exercise actual rejected HTTP requests and inspect their security log fields."""
import json
import secrets

from fastapi.testclient import TestClient


def events(caplog):
    return [json.loads(r.message) for r in caplog.records if r.name == "aeris.security"]


def test_login_failure_is_logged_without_credentials_or_query(client, caplog):
    password = secrets.token_urlsafe(24)
    query_marker = secrets.token_hex(12)
    unknown_user = "missing-" + secrets.token_hex(8)
    caller = TestClient(client.app)
    result = caller.post("/api/auth/login?private=" + query_marker, json={
        "username": unknown_user, "password": password})
    assert result.status_code == 401
    event, = events(caplog)
    assert event["event"] == "login_failed" and event["route"] == "/api/auth/login"
    assert event["status"] == 401 and "time" in event
    assert password not in caplog.text
    assert query_marker not in caplog.text
    assert unknown_user not in caplog.text


def test_role_and_csrf_denials_record_authenticated_actor_without_session(client, caplog):
    me = client.get("/api/auth/me").json()
    assert client.get("/api/admin/users").status_code == 403
    assert client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": secrets.token_urlsafe(16)}).status_code == 403
    recorded = events(caplog)
    assert len(recorded) == 2
    assert all(e["event"] == "access_denied" and e["actor_id"] == me["user"]["id"] for e in recorded)
    assert all(value not in caplog.text for value in (client.test_password, me["csrf_token"], client.cookies.get("aeris-local-session")))


def test_early_rate_and_foreign_origin_denials_are_logged_without_input(client, caplog):
    assert client.post("/api/scenarios", json={}, headers={"Origin": "https://private.example"}).status_code == 403
    # Fixture login already consumed one of the 60 allowed writes.
    for _ in range(59):
        client.post("/api/scenarios", json={})
    assert client.post("/api/scenarios", json={}).status_code == 429
    recorded = events(caplog)
    assert [e["event"] for e in recorded] == ["access_denied", "rate_limited"]
    assert recorded[0]["route"] == "/api/unmatched"
    assert "private.example" not in caplog.text

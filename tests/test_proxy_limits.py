"""A shared proxy must not turn each external client's limit into a group limit."""
import socket
import secrets
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import Settings, create_app


PROXY = "172.29.0.8"


@pytest.fixture
def shared(client, monkeypatch):
    original = socket.getaddrinfo

    def resolve(host, *args, **kwargs):
        if host == "caddy":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PROXY, 0))]
        return original(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    app = create_app(Settings(database_url=client.app.state.maintenance.pool.conninfo,
                              mode="shared", public_origin="https://testserver",
                              seed_demo=False, trusted_proxy_host="caddy"))
    with TestClient(app, base_url="https://testserver", client=(PROXY, 1234)) as peer:
        with app.state.maintenance.pool.connection() as conn:
            conn.execute("TRUNCATE aeris.login_limits")
        peer.test_password = client.test_password
        yield peer


def sign_in(peer, address, username="technician", password=None):
    return peer.post("/api/auth/login", headers={"X-Real-IP": address}, json={
        "username": username, "password": password or peer.test_password})


def test_one_proxy_client_cannot_exhaust_another_clients_write_limit(shared):
    for _ in range(60):
        assert shared.post("/api/nonexistent", json={}, headers={"X-Real-IP": "198.51.100.1"}).status_code == 404
    limited = shared.post("/api/nonexistent", json={}, headers={"X-Real-IP": "198.51.100.1"})
    assert limited.status_code == 429 and limited.headers["Retry-After"] == "60"
    signed_in = sign_in(shared, "198.51.100.2")
    assert signed_in.status_code == 200, signed_in.text
    assert "Secure" in signed_in.headers["set-cookie"]
    response = shared.post("/api/scenarios", headers={"X-Real-IP": "198.51.100.2",
        "X-CSRF-Token": signed_in.json()["csrf_token"]}, json={"request_id": str(uuid4()), "kind": "empty"})
    assert response.status_code == 201, response.text


def test_one_proxy_client_cannot_exhaust_another_clients_login_limit(shared):
    for i in range(30):
        assert sign_in(shared, "198.51.100.3", username=f"absent-{i}").status_code == 401
    limited = sign_in(shared, "198.51.100.3", username="absent-next")
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "LOGIN_RATE_LIMIT"
    response = sign_in(shared, "198.51.100.4")
    assert response.status_code == 200, response.text


def test_account_limit_still_spans_different_proxy_client_addresses(shared):
    for i in range(10):
        assert sign_in(shared, f"198.51.100.{i+20}", password=secrets.token_urlsafe(24)).status_code == 401
    result = sign_in(shared, "198.51.100.40")
    assert result.status_code == 429 and result.json()["error"]["code"] == "LOGIN_RATE_LIMIT"


def test_untrusted_peer_cannot_rotate_limit_using_forwarded_headers(client):
    stranger = TestClient(client.app, client=("198.51.100.45", 1234))
    for i in range(60):
        assert stranger.post("/api/nonexistent", json={}, headers={
            "X-Real-IP": f"203.0.113.{i+1}", "X-Forwarded-For": f"192.0.2.{i+1}",
            "Forwarded": f"for=192.0.2.{i+1}"}).status_code == 404
    assert stranger.post("/api/nonexistent", json={}, headers={"X-Real-IP": "203.0.113.200"}).status_code == 429


def test_write_and_login_use_the_same_identity_resolved_once(shared, monkeypatch):
    import app.main as boundary
    original_resolve = boundary.resolve_client_identity
    original_login = shared.app.state.accounts.login
    resolved, consumed = [], []

    def resolve(*args):
        result = original_resolve(*args)
        resolved.append(result)
        return result

    def login(command, peer):
        consumed.append(peer)
        return original_login(command, peer)

    monkeypatch.setattr(boundary, "resolve_client_identity", resolve)
    monkeypatch.setattr(shared.app.state.accounts, "login", login)
    assert sign_in(shared, "::ffff:198.51.100.9").status_code == 200
    assert resolved == consumed == ["198.51.100.9"]

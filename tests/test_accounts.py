"""Real PostgreSQL authentication, role, revocation and migration regressions."""
from concurrent.futures import ThreadPoolExecutor
import secrets
from uuid import uuid4

from fastapi.testclient import TestClient

from app.accounts import digest
from app.db import initialize


def fresh(client):
    return TestClient(client.app)


def login(client, username="admin", password=None):
    response = client.post("/api/auth/login", json={"username": username, "password": password or client.test_password})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()


def admin(client):
    login(client)
    return client


def create(client, role="technician", name=None):
    password = secrets.token_urlsafe(24)
    response = client.post("/api/admin/users", json={"username": name or "user-" + uuid4().hex[:10],
        "display_name": "New Specialist", "role": role, "password": password})
    assert response.status_code == 201, response.text
    return response.json(), password


def update(client, user, **extra):
    fields = {k: user[k] for k in ("display_name", "role", "active")}
    return client.patch("/api/admin/users/" + str(user["id"]), json=fields | {"expected_version": user["version"]} | extra)


def activate(client, username, password):
    session = login(client, username, password)
    assert session["user"]["must_change_password"]
    new = secrets.token_urlsafe(24)
    assert client.post("/api/auth/password", json={"current_password": password, "new_password": new}).status_code == 200
    return login(client, username, new)


def test_no_anonymous_or_legacy_bearer_data_access(client):
    stranger = fresh(client)
    for path in ("/api/overview", "/api/cases/missing", "/api/admin/users", "/api/admin/audit", "/api/auth/me"):
        assert stranger.get(path).status_code == 401
        assert stranger.get(path, headers={"Authorization": "Bearer " + secrets.token_urlsafe(32)}).status_code == 401
    assert stranger.post("/api/scenarios", json={"request_id": str(uuid4())}).status_code == 401
    assert stranger.get("/").status_code == 200  # public shell, no embedded records


def test_technician_cannot_manage_users_even_with_forged_client_role(client):
    for path in ("/api/admin/users", "/api/admin/audit"):
        assert client.get(path, headers={"X-Role": "admin"}).status_code == 403
    assert client.post("/api/admin/users", json={}).status_code == 403
    assert client.patch("/api/admin/users/" + str(uuid4()), json={}).status_code == 403
    assert client.post("/api/admin/users/" + str(uuid4()) + "/password", json={}).status_code == 403
    assert client.get("/api/overview").status_code == 200


def test_admin_can_read_everything_but_never_password_hashes(client):
    admin(client)
    users = client.get("/api/admin/users")
    assert users.status_code == 200 and len(users.json()["users"]) == 2
    assert "password_hash" not in users.text and client.test_password not in users.text
    assert client.get("/api/admin/audit").status_code == 200
    assert client.get("/api/overview").status_code == 200


def test_created_account_must_change_password_before_using_workspace(client):
    admin(client)
    user, password = create(client)
    other = fresh(client)
    activate(other, user["username"], password)
    assert other.get("/api/overview").status_code == 200
    assert other.get("/api/admin/users").status_code == 403
    with client.app.state.accounts.pool.connection() as conn:
        encoded = conn.execute("SELECT password_hash FROM aeris.users WHERE id=%s", (user["id"],)).fetchone()["password_hash"]
    assert encoded.startswith("$argon2id$") and password not in encoded


def test_temporary_password_gate_and_csrf_on_every_authenticated_write(client):
    admin(client)
    user, password = create(client)
    other = fresh(client)
    response = other.post("/api/auth/login", json={"username": user["username"], "password": password})
    assert response.status_code == 200
    assert other.get("/api/overview").json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"
    assert other.get("/api/admin/users").status_code == 403
    result = other.post("/api/auth/password", json={"current_password": password, "new_password": secrets.token_urlsafe(24)})
    assert result.status_code == 403 and result.json()["error"]["code"] == "CSRF_REQUIRED"
    assert client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": "wrong"}).status_code == 403


def test_password_change_revokes_all_sessions_and_old_password(client):
    other = fresh(client)
    login(other, "technician", client.test_password)
    new = "  a unique passphrase with spaces  "
    assert client.post("/api/auth/password", json={"current_password": client.test_password, "new_password": new}).status_code == 200
    assert client.get("/api/overview").status_code == other.get("/api/overview").status_code == 401
    assert client.post("/api/auth/login", json={"username": "technician", "password": client.test_password}).status_code == 401
    login(client, "technician", new)
    assert client.post("/api/auth/login", json={"username": "technician", "password": new.strip()}).status_code == 401


def test_logout_revokes_copied_cookie_and_login_rotates_session(client):
    stolen = fresh(client)
    stolen.cookies.update(client.cookies)
    assert client.post("/api/auth/logout", json={}).status_code == 200
    assert stolen.get("/api/auth/me").status_code == 401
    login(client, "technician")
    previous = client.cookies.get("aeris-local-session")
    login(client, "technician")
    assert client.cookies.get("aeris-local-session") != previous
    with client.app.state.accounts.pool.connection() as conn:
        assert not conn.execute("SELECT 1 FROM aeris.sessions WHERE token_hash=%s", (digest(previous),)).fetchone()


def test_deactivation_and_reactivation_preserve_identity_and_revoke_sessions(client):
    tech = fresh(client)
    login(tech, "technician", client.test_password)
    admin(client)
    user = next(u for u in client.get("/api/admin/users").json()["users"] if u["role"] == "technician")
    response = update(client, user, active=False)
    assert response.status_code == 200
    assert tech.get("/api/overview").status_code == 401
    assert tech.post("/api/auth/login", json={"username": "technician", "password": client.test_password}).status_code == 401
    assert update(client, response.json(), active=True).status_code == 200
    assert login(tech, "technician", client.test_password)["user"]["id"] == user["id"]
    assert update(client, user).json()["error"]["code"] == "STALE_VERSION"


def test_role_change_takes_effect_on_next_request(client):
    tech = fresh(client)
    login(tech, "technician", client.test_password)
    admin(client)
    user = next(u for u in client.get("/api/admin/users").json()["users"] if u["role"] == "technician")
    promoted = update(client, user, role="admin")
    assert promoted.status_code == 200 and tech.get("/api/overview").status_code == 401
    login(tech, "technician", client.test_password)
    assert tech.get("/api/admin/users").status_code == 200
    assert update(client, promoted.json(), role="technician").status_code == 200
    assert tech.get("/api/admin/users").status_code == 401
    login(tech, "technician", client.test_password)
    assert tech.get("/api/admin/users").status_code == 403


def test_last_admin_and_self_disable_are_blocked_and_audited_updates_have_no_secrets(client):
    admin(client)
    me = client.get("/api/auth/me").json()["user"]
    assert update(client, me, role="technician").json()["error"]["code"] == "LAST_ADMIN"
    assert update(client, me, active=False).json()["error"]["code"] == "LAST_ADMIN"
    create(client, "admin")
    assert update(client, me, active=False).json()["error"]["code"] == "SELF_PROTECTED"
    events = client.get("/api/admin/audit").json()["events"]
    assert any(e["action"] == "User created" for e in events)
    assert client.test_password not in str(events) and "csrf" not in str(events)


def test_admin_reset_requires_new_personal_password_and_revokes_prior_session(client):
    tech = fresh(client)
    login(tech, "technician", client.test_password)
    admin(client)
    user = next(u for u in client.get("/api/admin/users").json()["users"] if u["role"] == "technician")
    password = secrets.token_urlsafe(24)
    assert client.post(f"/api/admin/users/{user['id']}/password", json={"password": password, "expected_version": user["version"]}).status_code == 200
    assert tech.get("/api/auth/me").status_code == 401
    activate(tech, "technician", password)
    assert tech.get("/api/overview").status_code == 200


def test_unknown_fields_weak_passwords_and_duplicate_usernames_are_refused(client):
    admin(client)
    body = {"username": "valid-user", "display_name": "A Person", "password": secrets.token_urlsafe(24)}
    for extra in ({"password": "too-short"}, {"role": "superadmin"}, {"active": True}, {"display_name": "  "}):
        response = client.post("/api/admin/users", json=body | extra)
        assert response.status_code == 422 and body["password"] not in response.text
    assert client.post("/api/admin/users", json=body).status_code == 201
    assert client.post("/api/admin/users", json=body).status_code == 409


def test_idle_and_absolute_expiry_and_only_hashed_session_ids_are_stored(client):
    raw = client.cookies.get("aeris-local-session")
    with client.app.state.accounts.pool.connection() as conn:
        row = conn.execute("SELECT * FROM aeris.sessions WHERE token_hash=%s", (digest(raw),)).fetchone()
        assert row and raw not in str(row)
        conn.execute("UPDATE aeris.sessions SET last_seen_at=now()-interval '31 minutes'")
    assert client.get("/api/overview").status_code == 401
    login(client, "technician")
    with client.app.state.accounts.pool.connection() as conn:
        conn.execute("UPDATE aeris.sessions SET expires_at=now()-interval '1 minute'")
    assert client.get("/api/overview").status_code == 401


def test_login_failure_is_generic_and_database_throttle_survives_new_client(client):
    other = fresh(client)
    for name in ("missing", "technician"):
        assert other.post("/api/auth/login", json={"username": name, "password": "wrong"}).json()["error"]["code"] == "INVALID_CREDENTIALS"
    for _ in range(9):
        other.post("/api/auth/login", json={"username": "technician", "password": "wrong"})
    result = fresh(client).post("/api/auth/login", json={"username": "technician", "password": client.test_password})
    assert result.status_code == 429


def test_migration_is_repeatable_and_preserves_domain_evidence(client):
    sid = client.post("/api/scenarios", json={"request_id": str(uuid4()), "kind": "fault"}).json()["scenario_id"]
    before = client.get("/api/scenarios/" + sid).json()
    initialize(client.app.state.accounts.pool)
    initialize(client.app.state.accounts.pool)
    assert client.get("/api/scenarios/" + sid).json() == before
    assert client.get("/api/auth/me").status_code == 200


def test_review_identity_is_derived_from_account_not_body(client):
    sid = client.post("/api/scenarios", json={"request_id": str(uuid4()), "kind": "fault"}).json()["scenario_id"]
    result = client.put(f"/api/scenarios/{sid}/review", json={"request_id": str(uuid4()), "expected_version": client.get("/api/scenarios/" + sid).json()["scenario"]["version"],
        "reviewer": "Impersonated Administrator", "note": "An authenticated technical review.",
        "decisions": [{"risk_id": "yaw-drive", "decision": "Accepted"}, {"risk_id": "pitch-actuator", "decision": "Rejected"}]})
    assert result.status_code == 200
    review = client.get("/api/scenarios/" + sid).json()["forecast"]["review"]
    assert review["reviewer"] == "Test Technician" and review["reviewer_id"] == client.get("/api/auth/me").json()["user"]["id"]


def test_two_admins_cannot_concurrently_remove_all_administrators(client):
    tech = fresh(client)
    login(tech, "technician", client.test_password)
    admin(client)
    users = client.get("/api/admin/users").json()["users"]
    technician = next(u for u in users if u["role"] == "technician")
    administrator = next(u for u in users if u["role"] == "admin")
    promoted = update(client, technician, role="admin").json()
    login(tech, "technician", client.test_password)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: update(pair[0], pair[1], role="technician").status_code,
                                [(client, promoted), (tech, administrator)]))
    assert results.count(200) == 1 and all(code in {200, 401, 403, 409} for code in results)
    with client.app.state.accounts.pool.connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM aeris.users WHERE active AND role='admin'").fetchone()["n"] == 1


def test_host_recovery_revokes_sessions_and_cannot_promote_technician(client):
    from app.accounts import Recovery
    from app.domain import DomainError
    import pytest
    admin(client)
    store = client.app.state.accounts
    with pytest.raises(DomainError, match="active administrator"):
        store.recover_admin(Recovery(username="technician", password=secrets.token_urlsafe(24)))
    password = secrets.token_urlsafe(24)
    store.recover_admin(Recovery(username="admin", password=password))
    assert client.get("/api/admin/users").status_code == 401
    session = login(client, "admin", password)
    assert session["user"]["must_change_password"]
    assert client.get("/api/admin/users").status_code == 403

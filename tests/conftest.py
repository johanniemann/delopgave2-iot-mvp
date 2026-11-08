"""Integration tests are allowed to clear only a dedicated *_test database."""
import os
import secrets
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app.main import Settings, create_app
from app.accounts import NewUser


@pytest.fixture
def client():
    url = os.environ["DATABASE_URL"]
    if not urlsplit(url).path.endswith("_test"):
        pytest.fail("Refusing database cleanup: tests require a dedicated *_test database.")
    app = create_app(Settings(database_url=url, seed_demo=False))
    with TestClient(app) as client:
        with app.state.maintenance.pool.connection() as conn:
            conn.execute("TRUNCATE aeris.scenarios CASCADE")
            conn.execute("TRUNCATE aeris.users CASCADE")
            conn.execute("TRUNCATE aeris.login_limits")
        password = secrets.token_urlsafe(24)
        app.state.accounts.bootstrap(NewUser(username="admin", display_name="Test Administrator", password=password, role="admin"),
                                     NewUser(username="technician", display_name="Test Technician", password=password))
        client.test_password = password
        session = client.post("/api/auth/login", json={"username": "technician", "password": password}).json()
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        yield client

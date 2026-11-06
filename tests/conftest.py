"""Integration tests are allowed to clear only a dedicated *_test database."""
import os
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app.main import Settings, create_app


@pytest.fixture
def client():
    url = os.environ["DATABASE_URL"]
    if not urlsplit(url).path.endswith("_test"):
        pytest.fail("Refusing database cleanup: tests require a dedicated *_test database.")
    app = create_app(Settings(database_url=url, seed_demo=False))
    with TestClient(app) as client:
        with app.state.maintenance.pool.connection() as conn:
            conn.execute("TRUNCATE aeris.scenarios CASCADE")
        yield client

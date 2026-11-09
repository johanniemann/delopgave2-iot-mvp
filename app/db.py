"""PostgreSQL connection lifecycle and the prototype's initial versioned schema."""
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def open_pool(database_url: str) -> ConnectionPool:
    pool = ConnectionPool(database_url, min_size=1, max_size=5, open=False,
                          timeout=5, kwargs={"row_factory": dict_row, "connect_timeout": 5})
    pool.open()
    pool.wait(timeout=30)
    return pool


def initialize(pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(814017)")
        conn.execute(Path(__file__).with_name("schema.sql").read_text())

        for migration in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
            version = int(migration.name.split("_", 1)[0])
            if not conn.execute("SELECT 1 FROM aeris.schema_versions WHERE version=%s", (version,)).fetchone():
                conn.execute(migration.read_text())

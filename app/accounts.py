"""Individual accounts and server-side sessions; no public bootstrap or bearer bypass."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
import secrets
import sys
from typing import Literal
from uuid import UUID, uuid4

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from .domain import DomainError

# OWASP's Argon2id minimum, bounded for the small study-group VM.
PASSWORDS = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID)
PUBLIC = "id,username,display_name,role,active,must_change_password,version,created_at,updated_at"
ACCOUNT_LOCK = 814019


def digest(value):
    return sha256(value.encode()).hexdigest()


class AccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(AccountInput):
    username: str = Field(min_length=3, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize(cls, value):
        return value.strip().lower()


class Recovery(Login):
    password: SecretStr = Field(min_length=15, max_length=128)


class NewUser(Login):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9][a-z0-9._-]{2,63}$")
    password: SecretStr = Field(min_length=15, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)
    role: Literal["technician", "admin"] = "technician"

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Use at least two visible characters.")
        return value


class UpdateUser(AccountInput):
    expected_version: int = Field(ge=0)
    display_name: str = Field(min_length=2, max_length=80)
    role: Literal["technician", "admin"]
    active: bool
    _clean_name = field_validator("display_name")(NewUser.clean_name.__func__)


class ResetPassword(AccountInput):
    expected_version: int = Field(ge=0)
    password: SecretStr = Field(min_length=15, max_length=128)


class ChangePassword(AccountInput):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=15, max_length=128)


class Accounts:
    def __init__(self, pool):
        self.pool = pool
        self.dummy_hash = PASSWORDS.hash(secrets.token_urlsafe(32))

    def _audit(self, conn, actor_id, target_id, action, details=None):
        conn.execute("INSERT INTO aeris.account_audit(actor_id,target_id,action,details) VALUES (%s,%s,%s,%s)",
                     (actor_id, target_id, action, Jsonb(details or {})))

    def _verified(self, encoded, password):
        try:
            return PASSWORDS.verify(encoded, password)
        except (VerificationError, InvalidHashError):
            return False

    def _throttle(self, username, peer):
        allowed = True
        with self.pool.connection() as conn:
            conn.execute("DELETE FROM aeris.login_limits WHERE window_start < now()-interval '10 minutes'")
            for key, limit in (("peer:" + peer, 30), ("user:" + username, 10)):
                row = conn.execute("""INSERT INTO aeris.login_limits(key_hash) VALUES (%s)
                    ON CONFLICT(key_hash) DO UPDATE SET
                    attempts=CASE WHEN aeris.login_limits.window_start < now()-interval '5 minutes'
                                  THEN 1 ELSE aeris.login_limits.attempts+1 END,
                    window_start=CASE WHEN aeris.login_limits.window_start < now()-interval '5 minutes'
                                      THEN now() ELSE aeris.login_limits.window_start END
                    RETURNING attempts""", (digest(key),)).fetchone()
                if row["attempts"] > limit:
                    allowed = False
                    break
        if not allowed:
            raise DomainError("LOGIN_RATE_LIMIT", "Too many sign-in attempts. Try again in five minutes.", 429)

    def login(self, command, peer):
        self._throttle(command.username, peer)
        with self.pool.connection() as conn:
            user = conn.execute("SELECT * FROM aeris.users WHERE username=%s FOR UPDATE", (command.username,)).fetchone()
            valid = self._verified(user["password_hash"] if user else self.dummy_hash, command.password.get_secret_value())
            if not valid or not user or not user["active"]:
                raise DomainError("INVALID_CREDENTIALS", "Invalid username or password.", 401)
            if PASSWORDS.check_needs_rehash(user["password_hash"]):
                conn.execute("UPDATE aeris.users SET password_hash=%s WHERE id=%s",
                             (PASSWORDS.hash(command.password.get_secret_value()), user["id"]))
            conn.execute("DELETE FROM aeris.sessions WHERE expires_at < now() OR last_seen_at < now()-interval '30 minutes'")
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            expiry = datetime.now(timezone.utc) + timedelta(hours=8)
            conn.execute("INSERT INTO aeris.sessions(token_hash,user_id,csrf_token,expires_at) VALUES (%s,%s,%s,%s)",
                         (digest(token), user["id"], csrf, expiry))
        return token, {"user": {key: user[key] for key in PUBLIC.split(",")}, "csrf_token": csrf, "expires_at": expiry}

    def session(self, token):
        if not token or len(token) > 128:
            raise DomainError("AUTH_REQUIRED", "Sign in to open your workspace.", 401)
        with self.pool.connection() as conn:
            row = conn.execute("""UPDATE aeris.sessions s SET last_seen_at=now() FROM aeris.users u
                WHERE s.token_hash=%s AND s.user_id=u.id AND u.active
                AND s.expires_at>now() AND s.last_seen_at>now()-interval '30 minutes'
                RETURNING u.id,u.username,u.display_name,u.role,u.active,u.must_change_password,u.version,
                          u.created_at,u.updated_at,s.csrf_token,s.expires_at""", (digest(token),)).fetchone()
        if not row:
            raise DomainError("AUTH_REQUIRED", "Your session has ended. Please sign in again.", 401)
        return {"user": {key: row[key] for key in PUBLIC.split(",")},
                "csrf_token": row["csrf_token"], "expires_at": row["expires_at"], "session_hash": digest(token)}

    def logout(self, session):
        with self.pool.connection() as conn:
            conn.execute("DELETE FROM aeris.sessions WHERE token_hash=%s", (session["session_hash"],))

    def change_password(self, session, command):
        with self.pool.connection() as conn:
            user = conn.execute("SELECT * FROM aeris.users WHERE id=%s FOR UPDATE", (session["user"]["id"],)).fetchone()
            if not self._verified(user["password_hash"], command.current_password.get_secret_value()):
                raise DomainError("INVALID_CREDENTIALS", "The current password is incorrect.", 401)
            if self._verified(user["password_hash"], command.new_password.get_secret_value()):
                raise DomainError("PASSWORD_UNCHANGED", "Choose a different password.", 422)
            conn.execute("UPDATE aeris.users SET password_hash=%s,must_change_password=false,version=version+1,updated_at=now() WHERE id=%s",
                         (PASSWORDS.hash(command.new_password.get_secret_value()), user["id"]))
            conn.execute("DELETE FROM aeris.sessions WHERE user_id=%s", (user["id"],))
            self._audit(conn, user["id"], user["id"], "Password changed")

    def _admin(self, conn, session):
        # Serialize account changes and recheck the actor after acquiring the lock.
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (ACCOUNT_LOCK,))
        row = conn.execute("""SELECT u.id FROM aeris.users u JOIN aeris.sessions s ON s.user_id=u.id
            WHERE s.token_hash=%s AND u.active AND u.role='admin' AND NOT u.must_change_password
            AND s.expires_at>now() AND s.last_seen_at>now()-interval '30 minutes'""", (session["session_hash"],)).fetchone()
        if not row:
            raise DomainError("ADMIN_REQUIRED", "Administrator access is required.", 403)
        return row["id"]

    def list_users(self):
        with self.pool.connection() as conn:
            return conn.execute(f"SELECT {PUBLIC} FROM aeris.users ORDER BY active DESC,display_name,username").fetchall()

    def _insert(self, conn, command, temporary=True):
        return conn.execute(f"""INSERT INTO aeris.users(id,username,display_name,role,password_hash,must_change_password)
            VALUES (%s,%s,%s,%s,%s,%s) RETURNING {PUBLIC}""",
            (uuid4(), command.username, command.display_name, command.role,
             PASSWORDS.hash(command.password.get_secret_value()), temporary)).fetchone()

    def create_user(self, session, command):
        try:
            with self.pool.connection() as conn:
                actor = self._admin(conn, session)
                user = self._insert(conn, command)
                self._audit(conn, actor, user["id"], "User created", {"role": user["role"], "active": True})
                return user
        except UniqueViolation:
            raise DomainError("USERNAME_TAKEN", "That username is already in use.") from None

    def _target(self, conn, user_id, version):
        row = conn.execute("SELECT * FROM aeris.users WHERE id=%s FOR UPDATE", (user_id,)).fetchone()
        if not row:
            raise DomainError("USER_NOT_FOUND", "User not found.", 404)
        if row["version"] != version:
            raise DomainError("STALE_VERSION", "This account changed. Refresh before editing it.")
        return row

    def update_user(self, session, user_id, command):
        with self.pool.connection() as conn:
            actor = self._admin(conn, session)
            before = self._target(conn, user_id, command.expected_version)
            loses_admin = before["active"] and before["role"] == "admin" and (not command.active or command.role != "admin")
            if loses_admin:
                count = conn.execute("SELECT count(*) AS n FROM aeris.users WHERE active AND role='admin'").fetchone()["n"]
                if count <= 1:
                    raise DomainError("LAST_ADMIN", "Keep at least one active administrator.")
            if actor == user_id and (not command.active or command.role != "admin"):
                raise DomainError("SELF_PROTECTED", "Another administrator must change your role or deactivate you.")
            row = conn.execute(f"""UPDATE aeris.users SET display_name=%s,role=%s,active=%s,
                version=version+1,updated_at=now() WHERE id=%s RETURNING {PUBLIC}""",
                (command.display_name, command.role, command.active, user_id)).fetchone()
            # Revoke for identity edits too: no stale reviewer display identity.
            conn.execute("DELETE FROM aeris.sessions WHERE user_id=%s", (user_id,))
            self._audit(conn, actor, user_id, "User updated", {"role": row["role"], "active": row["active"], "display_name": row["display_name"]})
            return row

    def reset_password(self, session, user_id, command):
        with self.pool.connection() as conn:
            actor = self._admin(conn, session)
            user = self._target(conn, user_id, command.expected_version)
            if actor == user_id:
                raise DomainError("USE_OWN_PASSWORD", "Use Change password for your own account.", 422)
            conn.execute("UPDATE aeris.users SET password_hash=%s,must_change_password=true,version=version+1,updated_at=now() WHERE id=%s",
                         (PASSWORDS.hash(command.password.get_secret_value()), user_id))
            conn.execute("DELETE FROM aeris.sessions WHERE user_id=%s", (user_id,))
            self._audit(conn, actor, user["id"], "Password reset required")

    def audit(self):
        with self.pool.connection() as conn:
            return conn.execute("""SELECT a.id,a.action,a.details,a.occurred_at,a.actor_id,a.target_id,
                actor.display_name AS actor_name,target.username AS target_username
                FROM aeris.account_audit a LEFT JOIN aeris.users actor ON actor.id=a.actor_id
                JOIN aeris.users target ON target.id=a.target_id ORDER BY a.id DESC LIMIT 100""").fetchall()

    def bootstrap(self, command, technician=None):
        with self.pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (ACCOUNT_LOCK,))
            if conn.execute("SELECT 1 FROM aeris.users LIMIT 1").fetchone():
                raise DomainError("ALREADY_INITIALIZED", "Accounts already exist. Use an administrator account.")
            admin = self._insert(conn, command.model_copy(update={"role": "admin"}), temporary=technician is None)
            self._audit(conn, None, admin["id"], "Initial administrator created")
            if technician is not None:
                tech = self._insert(conn, technician.model_copy(update={"role": "technician"}), temporary=False)
                self._audit(conn, admin["id"], tech["id"], "Local demonstration technician created")

    def recover_admin(self, command):
        """Explicit host-only recovery; never promotes or activates an account."""
        with self.pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (ACCOUNT_LOCK,))
            user = conn.execute("SELECT id FROM aeris.users WHERE username=%s AND active AND role='admin' FOR UPDATE",
                                (command.username,)).fetchone()
            if not user:
                raise DomainError("ADMIN_NOT_FOUND", "An active administrator with that username is required.", 404)
            conn.execute("UPDATE aeris.users SET password_hash=%s,must_change_password=true,version=version+1,updated_at=now() WHERE id=%s",
                         (PASSWORDS.hash(command.password.get_secret_value()), user["id"]))
            conn.execute("DELETE FROM aeris.sessions WHERE user_id=%s", (user["id"],))
            self._audit(conn, None, user["id"], "Host administrator recovery")


def main():
    """Privileged host-side initial setup. JSON is read on stdin, never argv/logs."""
    from .db import initialize, open_pool
    import argparse
    parser = argparse.ArgumentParser(description="Host-side account setup/recovery; private JSON on stdin.")
    parser.add_argument("operation", choices=["bootstrap", "recover-admin"], nargs="?", default="bootstrap")
    operation = parser.parse_args().operation
    try:
        data = json.load(sys.stdin)
        if operation == "recover-admin":
            administrator = Recovery(**data)
            technician = None
        else:
            administrator = NewUser(**data["admin"])
            technician = NewUser(**data["technician"]) if data.get("technician") else None
    except (ValidationError, KeyError, ValueError):
        raise SystemExit("Invalid initial account input. Check username, display name and password length; no accounts changed.") from None
    if technician and os.environ.get("APP_MODE", "local") != "local":
        raise SystemExit("Demonstration accounts are restricted to loopback local mode.")
    pool = open_pool(os.environ["DATABASE_URL"])
    try:
        initialize(pool)
        accounts = Accounts(pool)
        if operation == "recover-admin":
            accounts.recover_admin(administrator)
            print("Administrator recovery recorded. Sign in and choose a new personal password.")
        else:
            accounts.bootstrap(administrator, technician)
            print("Initial accounts created. No credentials printed.")
    except DomainError as error:
        raise SystemExit(error.message) from None
    finally:
        pool.close()


if __name__ == "__main__":
    main()

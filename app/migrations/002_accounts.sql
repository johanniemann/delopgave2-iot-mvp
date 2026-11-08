-- Forward-only addition: preserve all v1 turbine/case evidence.
CREATE TABLE aeris.users (
    id uuid PRIMARY KEY,
    username text NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9][a-z0-9._-]{2,63}$'),
    display_name text NOT NULL,
    role text NOT NULL CHECK (role IN ('technician','admin')),
    active boolean NOT NULL DEFAULT true,
    password_hash text NOT NULL,
    must_change_password boolean NOT NULL DEFAULT true,
    version integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE aeris.sessions (
    token_hash text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES aeris.users,
    csrf_token text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);
CREATE INDEX sessions_by_user ON aeris.sessions(user_id);
CREATE TABLE aeris.login_limits (
    key_hash text PRIMARY KEY, window_start timestamptz NOT NULL DEFAULT now(),
    attempts integer NOT NULL DEFAULT 1
);
CREATE TABLE aeris.account_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id uuid REFERENCES aeris.users,
    target_id uuid NOT NULL REFERENCES aeris.users,
    action text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}',
    occurred_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO aeris.schema_versions(version) VALUES (2);

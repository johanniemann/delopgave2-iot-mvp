-- Version 1. All prototype objects are isolated in this schema.
-- Future changes require explicit forward migrations, not edits to live tables.
CREATE SCHEMA IF NOT EXISTS aeris;
CREATE TABLE IF NOT EXISTS aeris.schema_versions (
    version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS aeris.scenarios (
    id uuid PRIMARY KEY, turbine_id text NOT NULL DEFAULT 'WT-017',
    title text NOT NULL, kind text NOT NULL CHECK (kind IN ('fault','normal','invalid','empty')),
    created_at timestamptz NOT NULL, version integer NOT NULL DEFAULT 0,
    source text NOT NULL DEFAULT 'Interactive demo',
    fault_assessed_at timestamptz
);
CREATE TABLE IF NOT EXISTS aeris.readings (
    id uuid PRIMARY KEY, scenario_id uuid NOT NULL REFERENCES aeris.scenarios ON DELETE CASCADE,
    measured_at timestamptz NOT NULL, signal text NOT NULL DEFAULT 'wind_speed',
    value double precision, unit text NOT NULL DEFAULT 'm/s',
    quality text NOT NULL CHECK (quality IN ('Usable','Invalid')), reason text NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS readings_window ON aeris.readings (scenario_id, measured_at);
CREATE TABLE IF NOT EXISTS aeris.incidents (
    id text PRIMARY KEY, scenario_id uuid NOT NULL UNIQUE REFERENCES aeris.scenarios ON DELETE CASCADE,
    detected_at timestamptz NOT NULL, peak double precision NOT NULL,
    threshold double precision NOT NULL, code text NOT NULL, summary text NOT NULL, evidence jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS aeris.forecasts (
    id text PRIMARY KEY, scenario_id uuid NOT NULL UNIQUE REFERENCES aeris.scenarios ON DELETE CASCADE,
    generated_at timestamptz NOT NULL, model_version text NOT NULL,
    risks jsonb NOT NULL, source_reading_ids jsonb NOT NULL,
    review_status text NOT NULL DEFAULT 'Pending' CHECK (review_status IN ('Pending','Reviewed')),
    review jsonb
);
CREATE TABLE IF NOT EXISTS aeris.cases (
    id text PRIMARY KEY, scenario_id uuid NOT NULL UNIQUE REFERENCES aeris.scenarios ON DELETE CASCADE,
    incident_id text NOT NULL REFERENCES aeris.incidents,
    forecast_id text NOT NULL REFERENCES aeris.forecasts,
    status text NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Resolved')),
    created_at timestamptz NOT NULL, resolved_at timestamptz, accepted_risks jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS aeris.outcomes (
    id uuid PRIMARY KEY, case_id text NOT NULL REFERENCES aeris.cases ON DELETE CASCADE,
    external_reference text NOT NULL, all_work_complete boolean NOT NULL,
    verification text NOT NULL CHECK (verification IN ('Passed','Failed')),
    evidence_reference text NOT NULL, note text NOT NULL, created_at timestamptz NOT NULL,
    simulated boolean NOT NULL CHECK (simulated),
    UNIQUE (case_id, external_reference)
);
CREATE TABLE IF NOT EXISTS aeris.events (
    id uuid PRIMARY KEY, position bigint GENERATED ALWAYS AS IDENTITY,
    scenario_id uuid NOT NULL REFERENCES aeris.scenarios ON DELETE CASCADE,
    name text NOT NULL, occurred_at timestamptz NOT NULL, payload jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS events_window ON aeris.events (scenario_id, occurred_at);
CREATE TABLE IF NOT EXISTS aeris.commands (
    request_id uuid PRIMARY KEY, scenario_id uuid NOT NULL REFERENCES aeris.scenarios ON DELETE CASCADE,
    operation text NOT NULL, payload jsonb NOT NULL, result jsonb NOT NULL
);
INSERT INTO aeris.schema_versions(version) VALUES (1) ON CONFLICT DO NOTHING;

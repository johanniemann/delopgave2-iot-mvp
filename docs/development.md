# Run and change the prototype

## Start on your computer

Install Docker Desktop (or Docker Engine with Compose v2) and Git. Each contributor
uses their own clone. Python 3.10+ runs the small local setup/check scripts; the app
itself uses Python 3.13 inside Docker. No local Node or Python package install is
needed to run the dashboard.

From this repository's root:

```sh
python3 scripts/setup_demo.py
docker compose up -d --build --wait app
python3 scripts/setup_accounts.py
```

Open `http://localhost:8765` and sign in with an individual local account. Random
local Admin/Technician credentials are saved in ignored `.env.accounts-8765.json`;
see [account setup, permissions and recovery](authentication.md). The environment setup script creates an ignored `.env` with fresh
local credentials and never overwrites an existing file. Do not copy credentials
between members or commit `.env`.

Fresh settings also save a checkout-specific `COMPOSE_PROJECT_NAME`, so separate
clones do not replace each other's containers or attach a new password to the
same named database volume. Setup checks that its chosen loopback port is free
before creating the file. If 8765 is occupied, leave the existing installation
running and choose an unused port for the new checkout:

```sh
python3 scripts/setup_demo.py --port 8771
docker compose up -d --build --wait app
python3 scripts/setup_accounts.py
```

Open `http://localhost:8771`; local credentials are then in
`.env.accounts-8771.json`. For fresh settings, `--project aeris-local-second` can
select a new lowercase project name; an explicit `COMPOSE_PROJECT_NAME` or
`APP_PORT` environment variable is also honoured, including isolated CI jobs.
Choose a project name that is not already used by another installation. Keep the
saved name unchanged after data exists: changing it selects different containers
and volumes. `aeris-shared` is reserved for the separate shared deployment.

Existing `.env` files are preserved byte-for-byte, including older files without
a saved project name; rerunning setup does not apply overrides or change their
database password. To change only their local listening port, edit `APP_PORT`
deliberately and retain the original project and password. A port preflight is a
point-in-time check; Compose still refuses a port claimed by another process
later. Never delete a volume or regenerate a password to solve a port conflict.
The browser, JSON API and API reference are served by the same application. Swagger
UI at `/docs` uses FastAPI's standard CDN assets; `/openapi.json` and the dashboard
are available without those external assets.

PostgreSQL is a separate service with a named volume. It has no published database
port. Only the application is published, on the computer's loopback interface.
No Azure resource, firewall or auto-shutdown schedule is changed by these commands.

```sh
docker compose stop app db
```

Stops the prototype while preserving its database. Start again with
`docker compose up -d --wait app`. Do not use `down --volumes` for the demo: that deletes its persisted data.
New demo scenarios preserve all existing history; there is deliberately no wipe API.

## Try the complete workflow

1. On a new database, the overview contains one pending current forecast plus an
   open and a resolved sample case. Those records explicitly say Seeded demo history.
2. Select **New demo scenario -> High-wind event**. The app stores 96 synthetic
   readings, records the fault and generates an illustrated forecast. Existing
   data remains intact. Normal, invalid-data and custom windows are also available.
3. Accept/reject both risks, enter a review note and save. The numbers are fixed
   demo fixtures, not model results. A case stays blocked until both a current
   fault incident and a reviewed forecast exist. Rejecting every future risk does
   not erase the observed fault.
4. Create the predictive case. Inspect readings, the review and its event timeline.
5. **Simulate maintenance outcome**: first try Failed or Incomplete to leave the
   case Open. Then record Successful to demonstrate resolution. All returned
   evidence is visibly simulated; Better Maintenance itself is not built.
6. Reload: decisions and history remain. Restarting containers preserves them too.

## Optional monitoring and API walkthrough

The [local observability guide](observability.md) starts an isolated copy on port
8766 plus SigNoz on port 3301. It has separate data from the normal port-8765 demo
and stays off in the default/shared configuration. Use its helper to stop it when
finished. The [Postman guide](postman.md) demonstrates the complete case flow with
27 requests and 46 assertions. Neither workflow starts or deploys to Azure.

## Validation

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/check_repository.py
git diff --check
docker compose --profile test run --rm --build tests
python3 scripts/smoke_test.py
```

The smoke check needs the app running at the default port; set SMOKE_BASE_URL for
a different port. Tests use a separate `aeris_test` database with temporary storage.
They refuse to clear a database whose name does not end in `_test`. No SQLite
substitution or mocked database is used. Stop the test database when finished:

```sh
docker compose stop test-db
```

Application checks in GitHub Actions build/run the tests, build/deploy a fresh local
Compose environment, and check actual HTTP endpoints/assets. Newman 6.2.3 also runs the portable Postman
collection against that disposable local deployment. The job cleans up only
its isolated CI project. It does not deploy feature branches to Azure or receive
production secrets. Repository checks remain a separate lightweight job.

## Code map and dependencies

- `app/accounts.py` / `app/auth_routes.py`: hashed passwords, sessions, CSRF and two roles.
- `app/main.py`: HTTP routes, input/access guards, safe errors, lifecycle and assets.
- `app/schemas.py`: bounded request contracts; OpenAPI is the canonical route schema.
- `app/domain.py`: the explicit rule, case gate and resolution rule.
- `app/service.py`: transactions, state transitions, receipts, events and demo seeds.
- `app/telemetry.py`: opt-in bounded HTTP timing/count/span collection, no input export.
- `app/db.py` / `app/schema.sql`: PostgreSQL pool, initial schema v1 and forward migrations in `app/migrations/`.
- `app/static/`: English dashboard, accessible forms, charts and responsive layout.
- `tests/`: domain and actual PostgreSQL API/integration tests.
- `compose.yaml` / `Dockerfile`: repeatable local deployment and isolated test target.

`pyproject.toml` declares dependencies and `uv.lock` pins their complete resolution.
Docker runs `uv sync --frozen`. To change dependencies deliberately, use `uv add`
(or edit pyproject then `uv lock`), review the lockfile and rerun application checks.
Python/PostgreSQL images are pinned to official multi-platform image digests; review
and test updates. No frontend framework/build or chart service is required.
Schema version 1 initializes only this prototype's `aeris` schema. Future schema
changes require forward migrations and preservation of existing data; editing a
CREATE TABLE statement is not a migration for an already initialized database.

## Remote demonstration is a separate deployment decision

The [shared Azure deployment guide](deployment.md) contains the selected HTTPS
configuration, host preparation, release procedure and current verification state.
Local development continues to use only `compose.yaml`; the shared override is an
explicit deployment choice, not the default for every contributor.

Both local Docker and the shared Azure HTTPS demo have been verified. The shared
deployment uses its own PostgreSQL container/volume after inspecting the existing
VM; no legacy database was reused. Never open the DB port publicly. Keep the local
Compose option for every group member and use the deployment guide for releases.

Shared mode uses HTTPS through Caddy, explicit ALLOWED_HOSTS/PUBLIC_ORIGIN and
Secure HttpOnly individual session cookies. The new code always requires login,
including local mode; the old API_TOKEN cannot bypass roles. The existing Azure
release is unchanged until an authorized promotion. See [authentication](authentication.md)
for bootstrap and migration before release. Avoid exposing local HTTP mode publicly.
The developer's Mac has called the VM's real API over authenticated HTTPS and used
the public dashboard. Other teammates should still try it from their own computers;
an in-process test alone is not evidence of that access.


## Security and release checks (2026-11-17)

With uv 0.9.27 available, run `python3 scripts/security_checks.py`. The security
extra is locked in uv.lock and is not installed into the runtime image. The gate
blocks medium/high Bandit findings with medium/high confidence and any known
runtime dependency advisory returned by pip-audit. An unavailable audit service
fails the gate; there are no blanket vulnerability ignores.

CI also takes a private PostgreSQL dump, restores it into a generated disposable
database and compares saved domain/account evidence. See [release and recovery](release.md)
for the same operation on the selected environment and the image-promotion process.

Current candidate evidence on 2026-11-17: 99 application tests, 42 helper tests,
Newman 27 requests/46 assertions, HTTP smoke and a real backup/restore have passed.
Full case evidence remained identical after app/database restart. The installed
Azure release is recorded separately; these results do not establish promotion
or another person's review.

The opt-in proxy integration check runs the pinned Caddy image and two clients on
an internal Docker network, without host ports or database volumes:

```sh
python3 scripts/test_proxy_header_boundary.py --output .codex-log/caddy-header-proof.json
```

It requires the pinned Python and Caddy images already present (normal app build
and the CI Caddy validation prepare them). It checks 16 requests with forged or
duplicate headers and removes only its own temporary containers/network. CI runs
this check after Caddy configuration validation; importing the helper does not
start Docker.

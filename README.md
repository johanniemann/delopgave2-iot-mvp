# Aeris · Predictive Maintenance

An English technician dashboard and REST API for the group's Delopgave 2 prototype.
Inspect synthetic wind-turbine readings, assess a fault, review an illustrated
forecast, create a predictive case and record a simulated maintenance outcome.
**Predictive Maintenance only.** Better Maintenance is outside scope.

The API, review decisions, state rules, PostgreSQL persistence and event timeline
work. Sensor input, forecasts and external maintenance outcomes are synthetic.
There is no real AI inference, physical sensor connection, repair or verification.

## Start the dashboard

With Docker Desktop running, from this repository's root:

```sh
python3 scripts/setup_demo.py
docker compose up -d --build --wait app
python3 scripts/setup_accounts.py
```

Open **http://localhost:8765** and sign in as `admin` or `technician` using the
random credentials in ignored `.env.accounts-8765.json`. Admin adds/manages users;
Technician is the Maintenance specialist role. See [individual accounts](docs/authentication.md).
Each group member uses their own clone and local
settings. The setup script creates an ignored `.env` with random credentials;
it preserves existing settings. No local Python package or Node install is needed.
Docker runs Python 3.13; helper scripts need Python 3.10+.

Select **New demo scenario -> High-wind event**. Review both predicted risks, write
a note, save, then create a case. Try a failed simulated maintenance outcome before
a successful one. An incomplete/failed result keeps the case Open; a successful
simulated outcome resolves it. Reload to see persisted decisions and history.
Normal, invalid-data and custom-reading scenarios are also available.

The initial database contains clearly labelled Seeded demo history: one pending
forecast and two sample cases. This is illustrative history, not real human review.
Run the dashboard/database locally for development, or open the protected
[shared Azure dashboard](https://aeris-studiegruppe-linux.swedencentral.cloudapp.azure.com/)
when the VM is deliberately started. Its earlier installed release still uses the
shared token until the individual-account release is promoted. The VM shuts down at **00:00 Copenhagen time** and
must be started manually for the next session. See [deployment and verification](docs/deployment.md).

```sh
docker compose stop app db
```

Stops services while preserving data. Do not delete the named database volume.
The DB port is not published; the app binds to this computer's loopback interface.

## Validate changes

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/check_repository.py
git diff --check
docker compose --profile test run --rm --build tests
python3 scripts/smoke_test.py
```

Before running the HTTP smoke test, start the app and run `python3 scripts/setup_accounts.py`
as shown in [Start the dashboard](#start-the-dashboard). If you use a different port,
set `SMOKE_BASE_URL` to the app's URL. Docker tests use a separate temporary PostgreSQL
database and never clear demo data. On Windows use `python` or `py -3`.
GitHub Actions runs guidance checks, actual PostgreSQL tests, image builds and a
fresh local Docker deployment/HTTP smoke check. No feature branch deploys to Azure.

## Shared project guidance

- [Projektet forklaret på dansk uden tekniske forkundskaber](docs/project-walkthrough-da.md)
- [Run, demonstrate, test and maintain the prototype](docs/development.md)
- [Optional local SigNoz monitoring and safe failure test](docs/observability.md)
- [Individual logins, roles and user administration](docs/authentication.md)
- [Postman API walkthrough](docs/postman.md)
- [Shared Azure deployment and verification state](docs/deployment.md)
- [API contract, demo rule and state transitions](docs/api.md) · live OpenAPI at `/docs`
- [Project architecture, decisions and remaining work](docs/project-context.md)
- [Prototype scope and acceptance examples](docs/prototype-plan.md)
- [Course requirements and source register](docs/course-context.md)
- [Branch, PR and review workflow](CONTRIBUTING.md)
- [Using Codex, Claude Code, Cursor or Copilot](docs/agent-setup.md)
- [Canonical agent instructions](AGENTS.md) · [AI-use record](docs/ai-use.md)

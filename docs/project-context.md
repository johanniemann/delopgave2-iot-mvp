# Project context

## Observed baseline and current implementation

The initial README-only baseline was e1bfcef. The user clarified the Predictive
Maintenance-only scope and explicitly authorized implementation on 2026-11-06.
The current prototype implements an English dashboard, FastAPI REST endpoints,
PostgreSQL persistence, deterministic simulated forecasts, saved risk reviews,
case gates, simulated outcomes and an event timeline. Local Docker is the current
deployment; the existing Azure VM/database is not connected or verified here.

## Implemented structure

- `app/main.py` / `app/schemas.py`: API, validation, safe errors and access boundary.
- `app/domain.py`: synthetic rule (>28.0 m/s), case gate and resolution rule.
- `app/service.py`: transactional operations, version checks, replay receipts, seeds.
- `app/db.py` / `app/schema.sql`: pooled PostgreSQL access and initial schema v1.
- `app/static/`: same-origin HTML/CSS/JavaScript dashboard; no frontend build service.
- `tests/`: pure rules plus real PostgreSQL HTTP/integration tests.
- `compose.yaml` / `Dockerfile`: app + separate DB; isolated disposable test DB.
- `.github/workflows/application-checks.yml`: tests, image build, local Docker
  deployment and actual HTTP smoke check; no Azure/production secrets.
- `compose.shared.yaml` / `ops/Caddyfile`: optional shared-mode HTTPS boundary.
  Setup/release helpers and [deployment guide](deployment.md) preserve one stable
  Compose project and private settings across releases. Azure runtime verification
  remains separate from CI's local proxy/authentication checks.

State changes and domain events commit together. Row locks plus expected versions
prevent silent overwrites; request receipts and external references prevent duplicate
cases/outcomes. This is not event sourcing. Domain tests alone do not replace the
PostgreSQL tests. See [development instructions](development.md) and [API contract](api.md).

## Required product direction

The assignment's bounded MVP is predictive maintenance/notification in Managed
Services: receive a sensor value, evaluate a rule, produce an anomaly/alarm and
persist domain events/output in a separate database. The API must be callable from
another computer. The assignment allows Azure Cloud or local Docker, requires
CI/CD and a repository containing application and pipeline code. See
[the evidence and acceptance map](course-context.md).

Conceptual responsibilities (not existing directories or deployments):

```text
Remote caller -> REST input/validation -> domain rule -> result/event
                                             |              |
                                             +-- persistence+
                                                   separate DB
```

Keep transport and storage adapters from owning business decisions. A small
modular service is sufficient initially; no event broker, ML model, frontend,
Kubernetes cluster or database VM is required by the assignment.

## Selected prototype scope

The user's 2026-11-06 clarification selects **Predictive Maintenance only**, with a
visually usable English dashboard for technicians to inspect readings, faults,
forecasts and cases. The forecast is an explicitly simulated AI illustration, not
real predictive analysis. Synthetic readings may come from a VM-hosted database;
the browser accesses them through the application, never directly from the database.

The supplied diagram requires both a current fault incident and a reviewed forecast
before case creation. Forecast review precedes the case; case inspection remains
available afterwards. The user explicitly chose a labelled simulated external
maintenance outcome so the demo can record an outcome and resolve the original case.
Better Maintenance, its work orders, task assignment and operational verification
are excluded. The simulator is a boundary input, not a second maintenance system.

See the [prototype plan](prototype-plan.md) for the planned walkthrough, acceptance
examples, proposed simple architecture and implementation sequence. These team
choices add a dashboard to the academic minimum; they are not new course mandates.

## Relationship to Delopgave 1

The final student report proposes Predictive Maintenance and Better Maintenance as
two logical contexts, initially deployed together with separate model responsibilities.
That describes the broader original design; the selected prototype implements only
the first context. Do not interpret the report as permission to add the second.
It links wind-turbine measurements to cases, work orders and verified normal operation.
Earlier MD notes and API examples are proposals, not implemented contracts.

The report's NT-01 rule prevents work-order closure unless all required tasks are
complete and the latest verification confirms normal operation for their current
revision; changed work invalidates old verification. NH-01 proposes specialist
suggestions, with human assignment. Preserve these meanings if that broader scope
is later selected. Neither belongs in this prototype's implementation.
The report also proposes durable handoffs/outbox and replay handling for a later
cross-context integration. Do not introduce that infrastructure for simple telemetry
without a task that needs it. No Salesforce/Business Central integration is selected.

## Current decisions and remaining work

| Decision | Current evidence | When to resolve |
| --- | --- | --- |
| Language, framework and versions | Python 3.13/FastAPI, same-application HTML/CSS/JavaScript; exact dependencies in uv.lock and official base images pinned by digest | Review/test explicit upgrades; no extra frontend service |
| Database | PostgreSQL 16, separate Compose service and persistent named volume; objects isolated in aeris schema | Future schema changes need forward migrations; verify VM compatibility before reuse |
| Threshold, units and equality boundary | Synthetic wind_speed in m/s; strictly >28.0 opens fault, equality does not; invalid/null readings retained and excluded | A demo configuration, not an equipment safety limit |
| Forecast and notification | Fixed illustrative risks; saved human review; visible dashboard fault/review queue | No real inference, email/SMS or paid service |
| Deployment | Working local Compose architecture; DB port private, app loopback-only; shared-mode bearer guard exists | Azure/VM integration, TLS/shared access, shutdown schedule and a real second-computer API request remain unverified |
| Branch enforcement | Feature branches + independent PR review are team conventions | Hosting enforcement still not configured/verified by this implementation |

An architecture change should record the problem, alternatives, selected approach,
course/source connection and consequences here or in a focused decision note linked
here. Keep implemented facts separate from proposed changes. Do not add placeholder
runtime directories or pin a framework simply to make this instruction setup look complete.

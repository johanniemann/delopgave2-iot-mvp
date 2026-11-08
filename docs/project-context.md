# Project context

## Observed baseline and current implementation

The initial README-only baseline was e1bfcef. The user clarified the Predictive
Maintenance-only scope and explicitly authorized implementation on 2026-11-06.
The current prototype implements an English dashboard, FastAPI REST endpoints,
PostgreSQL persistence, deterministic simulated forecasts, saved risk reviews,
case gates, simulated outcomes and an event timeline. Local Docker remains the
development option. A shared HTTPS deployment now runs on the existing Azure VM
with a dedicated PostgreSQL container and persistent volume, not a reused legacy
database. External API access and the saved midnight shutdown schedule are verified;
see [deployment evidence and limits](deployment.md).

## Implemented structure

- `app/main.py` / `app/schemas.py`: API, validation, safe errors and access boundary.
- `app/domain.py`: synthetic rule (>28.0 m/s), case gate and resolution rule.
- `app/service.py`: transactional operations, version checks, replay receipts, seeds.
- `app/db.py` / `app/schema.sql`: pooled PostgreSQL access and initial schema v1.
- `app/static/`: same-origin HTML/CSS/JavaScript dashboard; no frontend build service.
- `app/telemetry.py`: optional app-scoped HTTP metrics/traces; off by default.
- `compose.observability.yaml` / `ops/observability/`: isolated local SigNoz demo.
- `postman/`: portable API walkthrough and assertions, also run in CI.
- `tests/`: pure rules plus real PostgreSQL HTTP/integration and telemetry tests.
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
| Deployment | Local Compose plus shared Azure Compose/Caddy HTTPS deployment; private DB, loopback app, shared bearer guard; Mac-to-VM API verified; midnight Copenhagen shutdown saved; actual VM deallocation/startup and saved evidence verified on 2026-11-07 | Other members still need to try shared access; actual scheduled stop has not been observed; release promotion is manual |
| Local observability | Opt-in OpenTelemetry SDK and self-hosted SigNoz on each developer's computer, separate Compose projects/data; bounded HTTP fields only; no SQL/body/token export | Team learning choice selected 2026-11-08; not deployed on the small Azure VM; see [monitoring guide](observability.md) |
| Branch enforcement | Feature branches + independent PR review are team conventions | Hosting enforcement still not configured/verified by this implementation |

On 2026-11-07 the owner explicitly authorized merging PR #4 after its five checks
passed because no other group member was available. The merge records this one-off
decision without claiming an independent review. The normal review convention stays
in place. The owner also selected the existing Azure hostname instead of adding
GitHub Pages or a separate public frontend. See the [Danish beginner walkthrough](project-walkthrough-da.md)
for the project's implementation, choices and course connections.

An architecture change should record the problem, alternatives, selected approach,
course/source connection and consequences here or in a focused decision note linked
here. Keep implemented facts separate from proposed changes. Do not add placeholder
runtime directories or pin a framework simply to make this instruction setup look complete.

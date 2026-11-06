# Project context

## Observed baseline and current implementation

At inspection on 2026-11-06, local HEAD and fetched origin/main contained only the
initial README (commit e1bfcef). There was no source code, dependency manifest,
Dockerfile, database configuration, test suite, CI or agent configuration.
This setup adds developer guidance and a repository-check workflow only.
The prototype scope was clarified on 2026-11-06; it is still preparation, not an
implemented application or permission to start building it.
Reinspect actual files as this status evolves; update this page with implementation.

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

## Open decisions, not assumptions

| Decision | Current evidence | When to resolve |
| --- | --- | --- |
| Language, framework and versions | Python/FastAPI with a same-application HTML/CSS/JavaScript dashboard is proposed, not installed or mandated | Confirm at the first authorized application increment; document versions and real commands |
| Database | Separate persistence required; PostgreSQL proposed, with identical demo data/schema locally or on the VM | Verify existing VM database before choosing reuse or a new service |
| Threshold, units and equality boundary | Exercise uses wind speed with an illustrative threshold; no validated project threshold | Acceptance examples before rule implementation |
| Notification | Visible in-dashboard fault/alert proposed; external delivery is not selected | Confirm the alert meets the observable flow; no paid email/SMS service by default |
| Deployment | Azure or local Docker permitted; local Compose is available; no container or Azure resource was started for this preparation | Verify actual VM services, database, access, cost and shutdown schedule before authorized deployment |
| Branch enforcement | Feature branches + PR review are the chosen working convention for this setup | Verify hosting plan/settings before claiming enforcement |

An architecture change should record the problem, alternatives, selected approach,
course/source connection and consequences here or in a focused decision note linked
here. Keep implemented facts separate from proposed changes. Do not add placeholder
runtime directories or pin a framework simply to make this instruction setup look complete.
